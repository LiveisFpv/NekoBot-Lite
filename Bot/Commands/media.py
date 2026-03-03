import asyncio
import os

from discord.ext import commands
from discord.ext.commands import Context

from services.lavalinkService import LavalinkService
from services.mediaPlaybackService import MediaPlaybackService
from services.mediaService import MediaPlayer
from utils.utils import log

try:
    import wavelink
except Exception:
    wavelink = None


if wavelink is not None:
    class NekoPlayer(wavelink.Player):
        async def _dispatch_voice_update(self) -> None:
            if self.guild is None:
                return

            data = self._voice_state.get("voice", {})
            session_id = data.get("session_id")
            token = data.get("token")
            endpoint = data.get("endpoint")

            channel_id = None
            channel = getattr(self, "channel", None)
            if channel is not None:
                channel_id = getattr(channel, "id", None)
            if channel_id is None:
                channel_id = data.get("channel_id")

            if not session_id or not token or not endpoint or not channel_id:
                return

            request = {
                "voice": {
                    "sessionId": session_id,
                    "token": token,
                    "endpoint": endpoint,
                    "channelId": str(channel_id),
                }
            }

            try:
                await self.node._update_player(self.guild.id, data=request)
            except Exception as exc:
                await log(f"ERROR: Failed to dispatch voice update with channelId: {exc}")
                await self.disconnect()
            else:
                self._connection_event.set()


class MediaCommands(commands.Cog):
    DEFAULT_VOLUME = int(os.getenv("PLAYER_DEFAULT_VOLUME", "100"))
    VOICE_CONNECT_TIMEOUT = float(os.getenv("VOICE_CONNECT_TIMEOUT", "45"))
    VOICE_CONNECT_RETRIES = int(os.getenv("VOICE_CONNECT_RETRIES", "2"))

    def __init__(self, bot):
        self.bot = bot
        self.players: dict[int, MediaPlayer] = {}
        self.progress_tasks: dict[int, asyncio.Task] = {}
        self.playback_service = MediaPlaybackService(default_volume=self.DEFAULT_VOLUME)
        self.lavalink_service = LavalinkService.from_env()

    def _cancel_progress_task(self, guild_id: int):
        task = self.progress_tasks.pop(guild_id, None)
        if task is not None and not task.done():
            task.cancel()

    def _start_progress_updater(self, guild_id: int, player, state: MediaPlayer):
        self._cancel_progress_task(guild_id)
        self.progress_tasks[guild_id] = asyncio.create_task(
            self._progress_updater(guild_id, player, state)
        )

    async def _progress_updater(self, guild_id: int, player, state: MediaPlayer):
        track_ref = player.current
        try:
            while True:
                if not getattr(player, "connected", False):
                    break

                if player.current is None:
                    break

                if player.current is not track_ref:
                    break

                await self.playback_service.publish_now_playing(
                    self.bot,
                    guild_id,
                    player,
                    state,
                    self._player_action_handler,
                )
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            return
        except Exception as exc:
            await log(f"WARNING: Progress updater failed for guild={guild_id}: {exc}")
        finally:
            current = self.progress_tasks.get(guild_id)
            if current is asyncio.current_task():
                self.progress_tasks.pop(guild_id, None)

    async def cog_load(self):
        # Avoid hanging tests that only load extensions.
        if os.getenv("PYTEST_CURRENT_TEST"):
            return

        await self.lavalink_service.connect(self.bot)

    async def get_player_state(self, guild_id: int) -> MediaPlayer:
        if guild_id not in self.players:
            self.players[guild_id] = MediaPlayer()
        return self.players[guild_id]

    async def _defer_if_interaction(self, ctx):
        interaction = getattr(ctx, "interaction", None)
        if interaction is None:
            return
        try:
            if hasattr(ctx, "defer"):
                await ctx.defer()
            elif not interaction.response.is_done():
                await interaction.response.defer(thinking=True)
        except Exception:
            pass

    async def _send_ctx_message(self, ctx, content: str):
        interaction = getattr(ctx, "interaction", None)
        if interaction is None:
            await ctx.send(content)
            return
        try:
            if interaction.response.is_done():
                await interaction.followup.send(content)
            else:
                await interaction.response.send_message(content)
        except Exception:
            await ctx.send(content)

    async def ensure_lavalink_ready(self, ctx) -> bool:
        if wavelink is None:
            await self._send_ctx_message(ctx, "Wavelink не установлен. Воспроизведение недоступно.")
            return False

        ready = await self.lavalink_service.ensure_connected(self.bot)
        if not ready:
            await self._send_ctx_message(ctx, "Lavalink сейчас недоступен. Попробуйте позже.")
            return False
        return True

    async def connect_to_channel(self, ctx):
        if ctx.author.voice is None or ctx.author.voice.channel is None:
            await self._send_ctx_message(ctx, "Вы не подключены к голосовому каналу.")
            return None

        channel = ctx.author.voice.channel
        voice_client = ctx.guild.voice_client

        if isinstance(voice_client, wavelink.Player):
            if voice_client.connected:
                if voice_client.channel != channel:
                    await voice_client.move_to(channel)
                player = voice_client
                player.autoplay = wavelink.AutoPlayMode.partial
                return player
            try:
                await voice_client.disconnect()
            except Exception:
                pass
            voice_client = None

        if voice_client is not None:
            try:
                await voice_client.disconnect(force=True)
            except Exception:
                await voice_client.disconnect()
            await asyncio.sleep(0.25)

        retries = max(1, self.VOICE_CONNECT_RETRIES)
        for attempt in range(1, retries + 1):
            try:
                player = await channel.connect(
                    cls=NekoPlayer,
                    self_deaf=True,
                    timeout=self.VOICE_CONNECT_TIMEOUT,
                    reconnect=True,
                )
                player.autoplay = wavelink.AutoPlayMode.partial
                return player
            except wavelink.ChannelTimeoutException as exc:
                await log(
                    f"WARNING: Voice connect timeout on attempt {attempt}/{retries} "
                    f"for guild={ctx.guild.id} channel={channel.id}: {exc}"
                )
                stale = ctx.guild.voice_client
                if stale is not None:
                    try:
                        await stale.disconnect(force=True)
                    except Exception:
                        try:
                            await stale.disconnect()
                        except Exception:
                            pass
                if attempt < retries:
                    await asyncio.sleep(1.0)
                    continue
                await self._send_ctx_message(
                    ctx,
                    "Не удалось подключиться к голосовому каналу (таймаут Discord). "
                    "Попробуйте еще раз через пару секунд.",
                )
                return None
            except Exception as exc:
                await log(
                    f"ERROR: Voice connect failed for guild={ctx.guild.id} "
                    f"channel={channel.id}: {exc}"
                )
                await self._send_ctx_message(
                    ctx,
                    "Не удалось подключиться к голосовому каналу. Проверьте права бота "
                    "(Connect/Speak) и попробуйте снова.",
                )
                return None

        return None

    async def _player_action_handler(self, action, interaction, view):
        guild = interaction.guild
        if guild is None:
            return

        player = guild.voice_client
        if not isinstance(player, wavelink.Player):
            return

        state = await self.get_player_state(guild.id)
        await self.playback_service.handle_view_response(action, player, state)
        if action == "stop":
            self._cancel_progress_task(guild.id)

        if player.connected:
            await self.playback_service.publish_now_playing(
                self.bot,
                guild.id,
                player,
                state,
                self._player_action_handler,
            )

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload):
        await log(f"INFO: Lavalink node connected: {payload.node.identifier} resumed={payload.resumed}")

    @commands.Cog.listener()
    async def on_wavelink_websocket_closed(self, payload):
        await log(
            "WARNING: Lavalink websocket closed for "
            f"guild={getattr(payload.player, 'guild', None)} code={payload.code} reason={payload.reason}"
        )

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload):
        player = payload.player
        if player is None or player.guild is None:
            return

        guild_id = player.guild.id
        state = await self.get_player_state(guild_id)
        await state.push_history(payload.track)

        await self.playback_service.publish_now_playing(
            self.bot,
            guild_id,
            player,
            state,
            self._player_action_handler,
        )
        self._start_progress_updater(guild_id, player, state)

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload):
        player = payload.player
        if player is None or player.guild is None:
            return
        self._cancel_progress_task(player.guild.id)

    @commands.Cog.listener()
    async def on_wavelink_track_exception(self, payload):
        player = payload.player
        if player is None:
            return

        await log(f"WARNING: Track exception: {payload.exception}")

    @commands.hybrid_command(name="play", help="Play a song from URL or search query")
    async def play(self, ctx, *, query: str):
        await self._defer_if_interaction(ctx)

        if not await self.ensure_lavalink_ready(ctx):
            return

        player = await self.connect_to_channel(ctx)
        if player is None:
            return

        guild_id = ctx.guild.id
        state = await self.get_player_state(guild_id)
        await state.set_output_channel(ctx.channel.id)
        await state.set_controller_message(ctx.channel.id, None)

        await self.playback_service.apply_queue_mode(player, state)

        try:
            result = await self.playback_service.enqueue_query(player, query)
        except Exception as exc:
            await log(f"ERROR: enqueue_query failed: {exc}")
            await self._send_ctx_message(ctx, "Не удалось загрузить трек по запросу.")
            return

        if result["added"] <= 0:
            await self._send_ctx_message(ctx, "Не удалось найти трек по запросу.")
            return

        if result["is_playlist"]:
            await self._send_ctx_message(
                ctx,
                f"Плейлист добавлен: **{result['title']}** (треков: {result['added']}).",
            )
        else:
            await self._send_ctx_message(ctx, f"Найден трек: {result['title']}")

        await self.playback_service.start_if_idle(player)

    @commands.hybrid_command(name="skip", help="Skip current track")
    async def skip(self, ctx=Context):
        player = ctx.guild.voice_client
        if not isinstance(player, wavelink.Player):
            await self._send_ctx_message(ctx, "Бот ничего не проигрывает в данный момент")
            return

        state = await self.get_player_state(ctx.guild.id)
        await self.playback_service.handle_view_response("skip", player, state)

    @commands.hybrid_command(name="pause", help="Pause current track")
    async def pause(self, ctx=Context):
        player = ctx.guild.voice_client
        if not isinstance(player, wavelink.Player) or not player.playing:
            await self._send_ctx_message(ctx, "Бот ничего не проигрывает в данный момент")
            return

        await player.pause(True)

    @commands.hybrid_command(name="resume", help="Resume current track")
    async def resume(self, ctx=Context):
        player = ctx.guild.voice_client
        if not isinstance(player, wavelink.Player) or not player.paused:
            await self._send_ctx_message(ctx, "Бот ничего не проигрывал до этого. Используйте %play команду")
            return

        await player.pause(False)

    @commands.hybrid_command(name="leave", help="Leave current voice channel")
    async def leave(self, ctx):
        player = ctx.guild.voice_client
        if not isinstance(player, wavelink.Player):
            await self._send_ctx_message(ctx, "Бот не подключён к голосовому каналу.")
            return

        state = await self.get_player_state(ctx.guild.id)
        self._cancel_progress_task(ctx.guild.id)
        await state.reset(queue=player.queue)
        if player.current is not None or player.playing or player.paused:
            await player.skip(force=True)
        await player.disconnect()
        await self._send_ctx_message(ctx, "Бот отключился от голосового канала.")


async def setup(bot):
    await bot.add_cog(MediaCommands(bot))
