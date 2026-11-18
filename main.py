import random
import json
import os
import math
import wave
import struct

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.graphics import Color, Ellipse, RoundedRectangle, Line, Rectangle
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.core.window import Window

Window.clearcolor = (0.043, 0.067, 0.125, 1)


def create_wav_sound(filename, base_freqs, duration=0.18, volume=0.5, is_coin=True):
    os.makedirs("coin_sounds", exist_ok=True)
    filepath = os.path.join("coin_sounds", filename)
    sample_rate = 22050
    try:
        with wave.open(filepath, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            total_samples = int(sample_rate * duration)
            frames = bytearray()
            num_f = len(base_freqs)
            for i in range(total_samples):
                t = i / sample_rate
                attack = min(1.0, t * 400.0)
                decay = math.exp(-t * (20.0 if is_coin else 11.0))
                env = attack * decay
                val = 0.0
                for idx, f in enumerate(base_freqs):
                    fm = 0.30 * math.sin(2 * math.pi * (f * 2.41) * t) * math.exp(-t * 35.0) if is_coin else 0.0
                    val += (1.0 / (idx + 1)) * math.sin(2 * math.pi * f * t + fm)
                val = (val / num_f) * env * volume
                int_val = max(-32767, min(32767, int(val * 32767)))
                frames.extend(struct.pack("<h", int_val))
            wf.writeframes(bytes(frames))
        return SoundLoader.load(filepath)
    except Exception:
        return None
class CoinBoardWidget(Widget):
    def __init__(self, game, **kwargs):
        super().__init__(**kwargs)
        self.game = game
        self.coin_labels = {}
        self.bind(pos=self.redraw, size=self.redraw)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.game.on_board_touch(touch.x, touch.y)
            return True
        return super().on_touch_down(touch)

    def get_cell_geometry(self):
        pad = 8
        avail_w = self.width - pad * 2
        avail_h = self.height - pad * 2
        cell = min(avail_w / self.game.cols, avail_h / self.game.rows)
        bw = cell * self.game.cols
        bh = cell * self.game.rows
        bx = self.x + (self.width - bw) / 2.0
        by = self.y + (self.height - bh) / 2.0
        return bx, by, bw, bh, cell

    def draw_3d_coin(self, cx, cy, radius, val, is_pulse=False):
        is_ice = str(val).startswith("ICE_")
        if val == "2X":
            label_txt = "2X"
            face_c, rim_c, shine_c, txt_c = self.game.palette.get("2X")
        elif is_ice:
            clean_v = int(str(val).replace("ICE_", ""))
            label_txt = f"${clean_v}"
            face_c, rim_c, shine_c, txt_c = self.game.palette.get(clean_v, self.game.default_style)
        else:
            label_txt = f"${val}"
            face_c, rim_c, shine_c, txt_c = self.game.palette.get(val, self.game.default_style)

        r = radius * (1.10 if is_pulse else 1.0)
        d = r * 2.0

        # 1. Drop Shadow
        Color(0.02, 0.03, 0.06, 0.65)
        Ellipse(pos=(cx - r + 3, cy - r - 6), size=(d, d))

        # 2. 3D Metallic Bottom Rim
        Color(*rim_c, 1)
        Ellipse(pos=(cx - r, cy - r - 4), size=(d, d))

        # 3. Main Coin Face
        Color(*face_c, 1)
        Ellipse(pos=(cx - r, cy - r + 1), size=(d, d))

        # 4. Inner Specular Highlight & Ring
        Color(*shine_c, 0.55)
        inner_r = r * 0.78
        Ellipse(pos=(cx - inner_r - 2, cy - inner_r + 3), size=(inner_r * 2, inner_r * 2))

        Color(*face_c, 1)
        core_r = r * 0.68
        Ellipse(pos=(cx - core_r, cy - core_r + 1), size=(core_r * 2, core_r * 2))

        # 5. Crisp Value Text
        lbl = Label(
            text=label_txt,
            font_size=int(r * (0.72 if len(label_txt) <= 3 else 0.58)),
            bold=True,
            color=(*txt_c, 1),
            size=(d, d),
            center=(cx, cy + 1)
        )
        lbl.texture_update()
        Color(1, 1, 1, 1)
        Rectangle(texture=lbl.texture, pos=(cx - lbl.texture_size[0] / 2, cy - lbl.texture_size[1] / 2 + 1), size=lbl.texture_size)

        # 6. Realistic Ice Cube Block & Frost Crystals for Frozen Coins!
        if is_ice:
            ice_r = r * 1.06
            ice_d = ice_r * 2.0
            # Translucent Cyan-White Ice Layer covering the coin
            Color(0.65, 0.92, 1.0, 0.48)
            RoundedRectangle(pos=(cx - ice_r, cy - ice_r), size=(ice_d, ice_d), radius=[12])
            # Glossy diagonal ice shine bar
            Color(1.0, 1.0, 1.0, 0.65)
            Line(points=[cx - ice_r * 0.55, cy + ice_r * 0.55, cx + ice_r * 0.55, cy - ice_r * 0.55], width=2.2)
            # Crisp Frost Border around Ice Block
            Color(0.88, 0.98, 1.0, 0.95)
            Line(rounded_rectangle=(cx - ice_r, cy - ice_r, ice_d, ice_d, 12), width=2.0)

    def redraw(self, *args):
        self.canvas.clear()
        bx, by, bw, bh, cell = self.get_cell_geometry()
        sx, sy = self.game.shake_offset

        with self.canvas:
            # Outer Gold Frame
            Color(0.98, 0.80, 0.08, 1)
            Line(rounded_rectangle=(bx - 4 + sx, by - 4 + sy, bw + 8, bh + 8, 14), width=2.5)

            # Grid Cells & Coins
            for r in range(self.game.rows):
                for c in range(self.game.cols):
                    # Kivy Y=0 is bottom, so row 0 (top) is at top of board
                    draw_r = (self.game.rows - 1) - r
                    cx_cell = bx + c * cell + sx
                    cy_cell = by + draw_r * cell + sy

                    Color(0.09, 0.14, 0.22, 1)
                    RoundedRectangle(pos=(cx_cell + 3, cy_cell + 3), size=(cell - 6, cell - 6), radius=[10])

                    val = self.game.grid[r][c]
                    if val is not None:
                        is_p = (self.game.pulse_timer > 0 and self.game.pulse_cell == (r, c))
                        self.draw_3d_coin(cx_cell + cell / 2.0, cy_cell + cell / 2.0, cell * 0.37, val, is_pulse=is_p)

            # Falling Animated Coin
            if self.game.anim_coin:
                ac = self.game.anim_coin
                ax = bx + ac["col"] * cell + cell / 2.0 + sx
                ay = ac["y"] + sy
                self.draw_3d_coin(ax, ay, cell * 0.37, ac["val"], is_pulse=False)

            # Gold & Color Sparks
            for p in self.game.particles:
                pr, pg, pb = p["color"]
                Color(pr, pg, pb, min(1.0, p["life"] / 15.0))
                s = p["size"]
                Ellipse(pos=(p["x"] - s + sx, p["y"] - s + sy), size=(s * 2, s * 2))
class CoinDrop3DGame(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.rows = 6
        self.cols = 5

        self.coin_tiers = (1, 2, 5, 10, 20, 50, 100, 200, 500)
        self.default_style = ((0.94, 0.27, 0.27), (0.50, 0.11, 0.11), (0.99, 0.79, 0.79), (1, 1, 1))
        self.palette = {
            1: ((0.80, 0.84, 0.88), (0.28, 0.33, 0.41), (0.97, 0.98, 0.99), (0.06, 0.09, 0.16)),
            2: ((0.22, 0.74, 0.97), (0.01, 0.41, 0.63), (0.73, 0.90, 0.99), (0.03, 0.18, 0.29)),
            5: ((0.98, 0.80, 0.08), (0.63, 0.38, 0.03), (0.99, 0.94, 0.54), (0.26, 0.13, 0.02)),
            10: ((0.98, 0.57, 0.24), (0.60, 0.20, 0.07), (0.99, 0.84, 0.67), (0.26, 0.08, 0.03)),
            20: ((0.64, 0.90, 0.21), (0.25, 0.38, 0.07), (0.93, 0.99, 0.80), (0.10, 0.18, 0.02)),
            50: ((0.96, 0.45, 0.71), (0.62, 0.09, 0.30), (0.98, 0.81, 0.91), (0.31, 0.03, 0.14)),
            100: ((0.75, 0.52, 0.99), (0.35, 0.11, 0.53), (0.95, 0.91, 1.00), (0.23, 0.03, 0.39)),
            200: ((0.18, 0.83, 0.75), (0.07, 0.37, 0.35), (0.80, 0.98, 0.95), (0.02, 0.18, 0.18)),
            500: ((0.94, 0.27, 0.27), (0.50, 0.11, 0.11), (0.99, 0.79, 0.79), (1.00, 1.00, 1.00)),
            "2X": ((0.02, 0.71, 0.83), (0.09, 0.31, 0.39), (0.99, 0.94, 0.54), (1.00, 1.00, 1.00)),
        }

        self.sounds = {
            "drop": create_wav_sound("k_drop.wav", (1450, 2890, 4320), 0.09, 0.45, True),
            "swap": create_wav_sound("k_swap.wav", (1100, 1760), 0.11, 0.40, True),
            "c1": create_wav_sound("k_c1.wav", (1318.5, 2637.0, 3951.0), 0.18, 0.55, True),
            "c2": create_wav_sound("k_c2.wav", (1568.0, 3136.0, 4698.6), 0.20, 0.58, True),
            "c3": create_wav_sound("k_c3.wav", (1975.5, 3951.0, 5274.0), 0.22, 0.60, True),
            "c4": create_wav_sound("k_c4.wav", (2093.0, 3136.0, 4186.0, 6272.0), 0.28, 0.65, True),
            "powerup": create_wav_sound("k_pow.wav", (880.0, 1318.5, 1760.0), 0.26, 0.55, False),
            "double": create_wav_sound("k_dbl.wav", (1046.5, 1568.0, 2093.0, 3136.0), 0.32, 0.62, True),
            "jackpot": create_wav_sound("k_jp.wav", (1046.5, 1318.5, 1568.0, 2093.0, 4186.0), 0.45, 0.70, True),
            "warning": create_wav_sound("k_warn.wav", (260, 195), 0.24, 0.50, False),
            "gameover": create_wav_sound("k_over.wav", (392.0, 311.13, 233.08), 0.38, 0.45, False),
        }

        self.grid = [[None for _ in range(self.cols)] for _ in range(self.rows)]
        self.score = 0
        self.high_score = self.load_high_score()
        self.combo_count = 0
        self.turn_counter = 0
        self.dry_turns = 0
        self.next_2x_turn = random.randint(18, 28)
        self.sound_on = True

        self.current_coin = self.get_random_coin()
        self.next_coin = self.get_random_coin()
        self.held_coin = None
        self.can_swap = True

        self.magnets_left = 1
        self.hammers_left = 1
        self.revives_used = 0
        self.magnet_ads_used = 0
        self.hammer_ads_used = 0
        self.max_booster_ads = 3

        self.active_tool = "DROP"
        self.anim_coin = None
        self.merge_timer = 0
        self.pending_focus = None

        self.particles = []
        self.shake_timer = 0
        self.shake_intensity = 0
        self.shake_offset = (0, 0)
        self.pulse_cell = None
        self.pulse_timer = 0

        self.modal_mode = None
        self.ad_timer = 0.0
        self.ad_callback = None

        self.build_ui()
        Clock.schedule_interval(self.update, 1.0 / 60.0)
    def build_ui(self):
        main_box = BoxLayout(orientation="vertical", padding=[12, 16, 12, 12], spacing=8)

        # Title & Score
        main_box.add_widget(Label(text="COIN DROP 3D", font_size="28sp", bold=True, color=(0.98, 0.80, 0.08, 1), size_hint_y=0.06))
        self.score_lbl = Label(text=f"Score: ${self.score}  |  Best: ${self.high_score}", font_size="17sp", bold=True, color=(0.97, 0.98, 0.99, 1), size_hint_y=0.05)
        main_box.add_widget(self.score_lbl)

        # HUD Bar: HOLD | READY | NEXT
        hud = BoxLayout(orientation="horizontal", spacing=10, size_hint_y=0.11, padding=[6, 4])
        self.btn_hold = Button(text="HOLD\nEMPTY", font_size="14sp", bold=True, background_normal="", background_color=(0.09, 0.14, 0.22, 1), color=(0.22, 0.74, 0.97, 1))
        self.btn_hold.bind(on_release=lambda x: self.swap_hold_coin())

        self.lbl_ready = Button(text=f"READY\n{self.fmt_coin(self.current_coin)}", font_size="18sp", bold=True, background_normal="", background_color=(0.98, 0.80, 0.08, 1), color=(0.1, 0.1, 0.1, 1))
        self.lbl_next = Button(text=f"NEXT\n{self.fmt_coin(self.next_coin)}", font_size="14sp", bold=True, background_normal="", background_color=(0.20, 0.25, 0.33, 1), color=(1, 1, 1, 1))

        hud.add_widget(self.btn_hold)
        hud.add_widget(self.lbl_ready)
        hud.add_widget(self.lbl_next)
        main_box.add_widget(hud)

        # 3D Coin Board Canvas
        self.board_widget = CoinBoardWidget(self, size_hint_y=0.58)
        main_box.add_widget(self.board_widget)

        # Status Label
        self.status_lbl = Label(text="Tap any column to drop coin", font_size="14sp", bold=True, color=(0.22, 0.74, 0.97, 1), size_hint_y=0.04)
        main_box.add_widget(self.status_lbl)

        # Power-up Buttons
        row1 = BoxLayout(orientation="horizontal", spacing=10, size_hint_y=0.07)
        self.btn_magnet = Button(text="Magnet (1)", font_size="15sp", bold=True, background_normal="", background_color=(0.15, 0.39, 0.92, 1))
        self.btn_magnet.bind(on_release=lambda x: self.activate_magnet())

        self.btn_hammer = Button(text="Hammer (1)", font_size="15sp", bold=True, background_normal="", background_color=(0.92, 0.35, 0.05, 1))
        self.btn_hammer.bind(on_release=lambda x: self.activate_hammer())

        row1.add_widget(self.btn_magnet)
        row1.add_widget(self.btn_hammer)
        main_box.add_widget(row1)

        # Sound & Restart Buttons
        row2 = BoxLayout(orientation="horizontal", spacing=10, size_hint_y=0.06)
        self.btn_sound = Button(text="Sound: ON", font_size="14sp", bold=True, background_normal="", background_color=(0.09, 0.64, 0.29, 1))
        self.btn_sound.bind(on_release=lambda x: self.toggle_sound())

        self.btn_restart = Button(text="Restart Game", font_size="14sp", bold=True, background_normal="", background_color=(0.86, 0.15, 0.15, 1))
        self.btn_restart.bind(on_release=lambda x: self.reset_game())

        row2.add_widget(self.btn_sound)
        row2.add_widget(self.btn_restart)
        main_box.add_widget(row2)

        self.add_widget(main_box)

        # Center Combo Banner Overlay
        self.banner_lbl = Label(
            text="", font_size="22sp", bold=True, color=(0.98, 0.80, 0.08, 1),
            size_hint=(0.8, 0.08), pos_hint={"center_x": 0.5, "center_y": 0.52}, opacity=0
        )
        self.add_widget(self.banner_lbl)

        # Modal Overlay Box for Ads & Game Over
        self.modal_box = BoxLayout(
            orientation="vertical", padding=20, spacing=12,
            size_hint=(0.85, 0.36), pos_hint={"center_x": 0.5, "center_y": 0.5}, opacity=0, disabled=True
        )
        with self.modal_box.canvas.before:
            Color(0.06, 0.09, 0.16, 0.96)
            self.modal_bg = RoundedRectangle(pos=self.modal_box.pos, size=self.modal_box.size, radius=[16])
        self.modal_box.bind(pos=self._update_modal_bg, size=self._update_modal_bg)

        self.modal_title = Label(text="", font_size="22sp", bold=True, color=(0.98, 0.80, 0.08, 1))
        self.modal_desc = Label(text="", font_size="15sp", halign="center", color=(0.9, 0.95, 1, 1))
        self.btn_modal_action = Button(text="", font_size="15sp", bold=True, background_normal="", background_color=(0.09, 0.64, 0.29, 1))
        self.btn_modal_action.bind(on_release=lambda x: self.on_modal_primary())

        self.btn_modal_close = Button(text="Restart Game", font_size="14sp", bold=True, background_normal="", background_color=(0.86, 0.15, 0.15, 1))
        self.btn_modal_close.bind(on_release=lambda x: self.reset_game())

        self.modal_box.add_widget(self.modal_title)
        self.modal_box.add_widget(self.modal_desc)
        self.modal_box.add_widget(self.btn_modal_action)
        self.modal_box.add_widget(self.btn_modal_close)
        self.add_widget(self.modal_box)

    def _update_modal_bg(self, *args):
        self.modal_bg.pos = self.modal_box.pos
        self.modal_bg.size = self.modal_box.size
    def fmt_coin(self, val):
        if val is None:
            return "EMPTY"
        if val == "2X":
            return "2X"
        if str(val).startswith("ICE_"):
            return f"ICE ${str(val).replace('ICE_', '')}"
        return f"${val}"

    def play_sound(self, kind, combo=1):
        if not self.sound_on:
            return
        key = f"c{min(4, combo)}" if kind == "merge" else kind
        snd = self.sounds.get(key)
        if snd:
            try:
                if snd.state == "play":
                    snd.stop()
                snd.play()
            except Exception:
                pass

    def toggle_sound(self):
        self.sound_on = not self.sound_on
        self.refresh_ui()

    def load_high_score(self):
        try:
            if os.path.exists("coindrop_highscore.json"):
                with open("coindrop_highscore.json", "r") as f:
                    return json.load(f).get("high_score", 0)
        except Exception:
            pass
        return 0

    def save_high_score(self):
        if self.score > self.high_score:
            self.high_score = self.score
            try:
                with open("coindrop_highscore.json", "w") as f:
                    json.dump({"high_score": self.high_score}, f)
            except Exception:
                pass

    def show_banner(self, text, sec=0.8):
        self.banner_lbl.text = text
        self.banner_lbl.opacity = 1
        Clock.unschedule(self._hide_banner)
        Clock.schedule_once(self._hide_banner, sec)

    def _hide_banner(self, dt):
        self.banner_lbl.opacity = 0

    def trigger_shake(self, intensity=6, frames=12):
        self.shake_intensity = intensity
        self.shake_timer = frames

    def spawn_sparks(self, cx, cy, color, count=18):
        spark_cols = (color, (0.98, 0.80, 0.08), (1, 1, 1))
        for _ in range(count):
            ang = random.uniform(0, 2 * math.pi)
            spd = random.uniform(2.0, 7.5)
            self.particles.append({
                "x": cx, "y": cy,
                "vx": math.cos(ang) * spd,
                "vy": math.sin(ang) * spd,
                "life": random.randint(15, 25),
                "size": random.uniform(2.5, 5.0),
                "color": random.choice(spark_cols)
            })

    def get_random_coin(self):
        self.turn_counter += 1
        if self.turn_counter >= self.next_2x_turn:
            delay = 22 if self.score < 3000 else (30 if self.score < 10000 else 40)
            self.next_2x_turn = self.turn_counter + random.randint(delay, delay + 12)
            return "2X"

        # Ice chance reduced significantly so Ice Coins appear rarely!
        if self.score < 2500:
            pool = (1, 1, 2, 2, 5, 10)
            anti_chance, ice_chance = 0.72, 0.0
        elif self.score < 7500:
            pool = (1, 2, 5, 5, 10, 20)
            anti_chance, ice_chance = 0.80, 0.08
        elif self.score < 18000:
            pool = (1, 2, 5, 10, 20, 50)
            anti_chance, ice_chance = 0.88, 0.14
        else:
            pool = (2, 5, 10, 20, 50, 100)
            anti_chance, ice_chance = 0.94, 0.20

        top_coins = set()
        for c in range(self.cols):
            for r in range(self.rows):
                val = self.grid[r][c]
                if val is not None:
                    clean_v = int(str(val).replace("ICE_", "")) if "ICE_" in str(val) else val
                    top_coins.add(clean_v)
                    break

        hard_choices = [x for x in pool if x not in top_coins]
        choice = random.choice(hard_choices) if (hard_choices and random.random() < anti_chance) else random.choice(pool)

        if ice_chance > 0 and random.random() < ice_chance:
            return f"ICE_{choice}"
        return choice
    def swap_hold_coin(self):
        if self.anim_coin or self.merge_timer > 0 or self.modal_mode:
            return
        if self.current_coin == "2X":
            self.show_banner("2X CANNOT BE HELD!")
            return
        if not self.can_swap:
            self.show_banner("DROP A COIN FIRST!")
            return

        self.play_sound("swap")
        if self.held_coin is None:
            self.held_coin = self.current_coin
            self.current_coin = self.next_coin
            self.next_coin = self.get_random_coin()
            self.show_banner("SAVED TO HOLD!")
        else:
            self.held_coin, self.current_coin = self.current_coin, self.held_coin
            self.show_banner("SWAPPED!")
        self.can_swap = False
        self.refresh_ui()

    def start_ad(self, title, callback):
        self.modal_mode = "AD"
        self.ad_timer = 5.0
        self.ad_callback = callback
        self.modal_title.text = "SPONSORED VIDEO AD"
        self.modal_desc.text = f"Reward: {title}\nAd ends in 5s..."
        self.btn_modal_action.opacity = 0
        self.btn_modal_action.disabled = True
        self.btn_modal_close.opacity = 0
        self.btn_modal_close.disabled = True
        self.modal_box.opacity = 1
        self.modal_box.disabled = False

    def activate_magnet(self):
        if self.anim_coin or self.merge_timer > 0 or self.modal_mode:
            return
        if self.magnets_left <= 0:
            if self.magnet_ads_used < self.max_booster_ads:
                rem = self.max_booster_ads - self.magnet_ads_used
                self.start_ad(f"+1 Magnet ({rem} Ads left)", self.grant_ad_magnet)
            else:
                self.show_banner("MAX MAGNET ADS USED!")
            return

        bx, by, _, _, cell = self.board_widget.get_cell_geometry()
        collected = 0
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] in (1, 2):
                    collected += self.grid[r][c]
                    draw_r = (self.rows - 1) - r
                    self.spawn_sparks(bx + (c + 0.5) * cell, by + (draw_r + 0.5) * cell, (0.22, 0.74, 0.97), 14)
                    self.grid[r][c] = None

        if collected > 0:
            self.magnets_left -= 1
            self.score += collected * 5
            self.save_high_score()
            self.play_sound("powerup")
            self.trigger_shake(7, 14)
            self.apply_gravity()
            self.show_banner(f"MAGNET! +${collected * 5}")
            self.pending_focus = (self.rows - 1, 0)
            self.merge_timer = 16
        else:
            self.show_banner("NO $1 OR $2 COINS!")
        self.refresh_ui()

    def grant_ad_magnet(self):
        self.magnet_ads_used += 1
        self.magnets_left += 1
        self.show_banner("+1 MAGNET UNLOCKED!")
        self.refresh_ui()

    def activate_hammer(self):
        if self.anim_coin or self.merge_timer > 0 or self.modal_mode:
            return
        if self.hammers_left <= 0:
            if self.hammer_ads_used < self.max_booster_ads:
                rem = self.max_booster_ads - self.hammer_ads_used
                self.start_ad(f"+1 Hammer ({rem} Ads left)", self.grant_ad_hammer)
            else:
                self.show_banner("MAX HAMMER ADS USED!")
            return

        self.active_tool = "DROP" if self.active_tool == "HAMMER" else "HAMMER"
        self.refresh_ui()

    def grant_ad_hammer(self):
        self.hammer_ads_used += 1
        self.hammers_left += 1
        self.active_tool = "HAMMER"
        self.show_banner("+1 HAMMER UNLOCKED!")
        self.refresh_ui()

    def on_board_touch(self, tx, ty):
        if self.anim_coin or self.merge_timer > 0 or self.modal_mode:
            return
        bx, by, bw, bh, cell = self.board_widget.get_cell_geometry()
        if not (bx <= tx < bx + bw and by <= ty < by + bh):
            return

        col = int((tx - bx) // cell)
        draw_r = int((ty - by) // cell)
        row = (self.rows - 1) - draw_r

        if self.active_tool == "HAMMER":
            if self.grid[row][col] is not None:
                self.spawn_sparks(bx + (col + 0.5) * cell, by + (draw_r + 0.5) * cell, (0.98, 0.57, 0.24), 22)
                self.trigger_shake(8, 14)
                self.grid[row][col] = None
                self.hammers_left -= 1
                self.active_tool = "DROP"
                self.play_sound("powerup")
                self.apply_gravity()
                self.show_banner("SMASHED!")
                self.pending_focus = (row, col)
                self.merge_timer = 14
                self.refresh_ui()
            return

        target_row = -1
        for r in range(self.rows - 1, -1, -1):
            if self.grid[r][col] is None:
                target_row = r
                break

        if target_row == -1:
            self.show_banner("COLUMN FULL!")
            return

        val = self.current_coin
        self.current_coin = self.next_coin
        self.next_coin = self.get_random_coin()
        self.can_swap = True
        self.combo_count = 0

        target_draw_r = (self.rows - 1) - target_row
        target_y = by + (target_draw_r + 0.5) * cell
        start_y = by + bh + cell * 0.3
        self.anim_coin = {"col": col, "y": start_y, "target_y": target_y, "val": val, "row": target_row}
        self.refresh_ui()
    def trigger_2x_coin(self, r, c):
        bx, by, _, _, cell = self.board_widget.get_cell_geometry()
        self.grid[r][c] = None
        draw_r = (self.rows - 1) - r
        self.spawn_sparks(bx + (c + 0.5) * cell, by + (draw_r + 0.5) * cell, (0.02, 0.71, 0.83), 26)

        doubled_any = False
        jackpot_hit = False
        focus_r, focus_c = r, c

        for dr, dc in ((1, 0), (-1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.rows and 0 <= nc < self.cols:
                adj_val = self.grid[nr][nc]
                nd_r = (self.rows - 1) - nr
                ncx, ncy = bx + (nc + 0.5) * cell, by + (nd_r + 0.5) * cell

                if str(adj_val).startswith("ICE_"):
                    self.grid[nr][nc] = int(str(adj_val).replace("ICE_", ""))
                    self.spawn_sparks(ncx, ncy, (0.65, 0.92, 1.0), 18)
                    doubled_any = True
                    focus_r, focus_c = nr, nc
                elif isinstance(adj_val, int):
                    if adj_val >= 500:
                        self.grid[nr][nc] = None
                        self.score += 2500
                        jackpot_hit = True
                        self.spawn_sparks(ncx, ncy, (0.94, 0.27, 0.27), 32)
                    else:
                        upgraded = self.get_next_tier(adj_val)
                        self.grid[nr][nc] = upgraded
                        self.score += upgraded
                        self.spawn_sparks(ncx, ncy, (0.98, 0.80, 0.08), 18)
                    doubled_any = True
                    focus_r, focus_c = nr, nc

        if jackpot_hit:
            self.play_sound("jackpot")
            self.trigger_shake(11, 16)
            self.show_banner("$500 JACKPOT +$2500!")
        else:
            self.play_sound("double")
            self.trigger_shake(8, 14)
            self.show_banner("2X DOUBLED!" if doubled_any else "2X USED!")

        self.save_high_score()
        self.apply_gravity()
        self.pending_focus = (focus_r, focus_c)
        self.merge_timer = 15
        self.refresh_ui()

    def get_next_tier(self, val):
        if val in self.coin_tiers:
            idx = self.coin_tiers.index(val)
            if idx + 1 < len(self.coin_tiers):
                return self.coin_tiers[idx + 1]
        return 500

    def step_merges(self):
        bx, by, _, _, cell = self.board_widget.get_cell_geometry()
        focus_r, focus_c = self.pending_focus
        merged = False
        check_order = [(focus_r, focus_c)] + [
            (r, c) for r in range(self.rows - 1, -1, -1) for c in range(self.cols)
        ]

        for r, c in check_order:
            val = self.grid[r][c]
            if not isinstance(val, int):
                continue

            neighbors = []
            for dr, dc in ((1, 0), (-1, 0), (0, -1), (0, 1)):
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.rows and 0 <= nc < self.cols and self.grid[nr][nc] == val:
                    neighbors.append((nr, nc))

            if neighbors:
                draw_r = (self.rows - 1) - r
                cx, cy = bx + (c + 0.5) * cell, by + (draw_r + 0.5) * cell
                self.combo_count += 1

                for dr, dc in ((1, 0), (-1, 0), (0, -1), (0, 1)):
                    ir, ic = r + dr, c + dc
                    if 0 <= ir < self.rows and 0 <= ic < self.cols:
                        cell_v = str(self.grid[ir][ic])
                        if cell_v.startswith("ICE_"):
                            self.grid[ir][ic] = int(cell_v.replace("ICE_", ""))
                            id_r = (self.rows - 1) - ir
                            self.spawn_sparks(bx + (ic + 0.5) * cell, by + (id_r + 0.5) * cell, (0.65, 0.92, 1.0), 14)
                            self.show_banner("ICE MELTED!")

                if val >= 500:
                    for nr, nc in neighbors:
                        self.grid[nr][nc] = None
                    self.grid[r][c] = None
                    self.score += 2500 * self.combo_count
                    self.play_sound("jackpot")
                    self.spawn_sparks(cx, cy, (0.94, 0.27, 0.27), 38)
                    self.trigger_shake(11, 16)
                    self.show_banner(f"RUBY BLAST +${2500 * self.combo_count}!")
                else:
                    new_val = self.get_next_tier(val)
                    for nr, nc in neighbors:
                        self.grid[nr][nc] = None
                    self.grid[r][c] = new_val
                    self.score += new_val * self.combo_count
                    self.play_sound("merge", self.combo_count)

                    face_col, _, _, _ = self.palette.get(new_val, self.default_style)
                    self.spawn_sparks(cx, cy, face_col, 16 + self.combo_count * 5)
                    if self.combo_count >= 2:
                        self.trigger_shake(min(10, 3 + self.combo_count * 2), 12)
                    if self.combo_count > 1:
                        self.show_banner(f"{self.combo_count}X COMBO!")

                if self.combo_count == 5:
                    self.magnets_left += 1
                    self.show_banner("5X COMBO +1 MAGNET!")
                elif self.combo_count >= 6:
                    self.hammers_left += 1
                    self.show_banner("6X COMBO +1 HAMMER!")

                self.save_high_score()
                merged = True
                self.pending_focus = (r, c)
                break

        if merged:
            self.dry_turns = 0
            self.apply_gravity()
            self.pulse_cell = self.pending_focus
            self.pulse_timer = 10
            self.merge_timer = 14
        else:
            self.pending_focus = None
            if self.combo_count == 0:
                self.dry_turns += 1
                if self.dry_turns >= 12:
                    self.push_up_row()
                    return
            top_row = next(iter(self.grid))
            if all(cell is not None for cell in top_row):
                self.open_gameover("All columns are full!")
        self.refresh_ui()

    def push_up_row(self):
        top_row = next(iter(self.grid))
        if any(cell is not None for cell in top_row):
            self.open_gameover("12 turns without a merge! Board overflowed!")
            return
        for r in range(self.rows - 1):
            self.grid[r] = self.grid[r + 1][:]
        new_bottom = []
        choices = (1, 2, 5, 10)
        for c in range(self.cols):
            above = self.grid[self.rows - 2][c]
            left = new_bottom[c - 1] if c > 0 else None
            valid = [x for x in choices if x != above and x != left]
            new_bottom.append(random.choice(valid if valid else choices))
        self.grid[self.rows - 1] = new_bottom
        self.dry_turns = 0
        self.play_sound("warning")
        self.trigger_shake(8, 14)
        self.show_banner("BOARD PUSHED UP!")
        self.refresh_ui()
    def apply_gravity(self):
        for c in range(self.cols):
            items = [self.grid[r][c] for r in range(self.rows) if self.grid[r][c] is not None]
            new_col = [None] * (self.rows - len(items)) + items
            for r in range(self.rows):
                self.grid[r][c] = new_col[r]

    def open_gameover(self, reason):
        self.play_sound("gameover")
        self.modal_mode = "GAMEOVER"
        self.modal_title.text = "BOARD FULL!"
        self.modal_desc.text = f"{reason}\nScore: ${self.score}  |  Best: ${self.high_score}"
        if self.revives_used < 1:
            self.btn_modal_action.text = "Watch Ad to Revive (1 Chance)"
            self.btn_modal_action.opacity = 1
            self.btn_modal_action.disabled = False
        else:
            self.btn_modal_action.opacity = 0
            self.btn_modal_action.disabled = True
        self.btn_modal_close.opacity = 1
        self.btn_modal_close.disabled = False
        self.modal_box.opacity = 1
        self.modal_box.disabled = False

    def on_modal_primary(self):
        if self.modal_mode == "GAMEOVER" and self.revives_used < 1:
            self.start_ad("Clear Bottom 2 Rows & Continue!", self.execute_revive)

    def execute_revive(self):
        bx, by, _, _, cell = self.board_widget.get_cell_geometry()
        self.revives_used += 1
        for r in (self.rows - 1, self.rows - 2):
            for c in range(self.cols):
                if self.grid[r][c] is not None:
                    draw_r = (self.rows - 1) - r
                    self.spawn_sparks(bx + (c + 0.5) * cell, by + (draw_r + 0.5) * cell, (0.09, 0.64, 0.29), 14)
                    self.grid[r][c] = None
        self.dry_turns = 0
        self.apply_gravity()
        self.trigger_shake(8, 14)
        self.show_banner("REVIVED! (0 Left)")
        self.pending_focus = (self.rows - 1, 0)
        self.merge_timer = 14
        self.refresh_ui()

    def reset_game(self):
        self.modal_mode = None
        self.modal_box.opacity = 0
        self.modal_box.disabled = True
        self.grid = [[None for _ in range(self.cols)] for _ in range(self.rows)]
        self.score = 0
        self.combo_count = 0
        self.turn_counter = 0
        self.dry_turns = 0
        self.next_2x_turn = random.randint(18, 28)
        self.magnets_left = 1
        self.hammers_left = 1
        self.revives_used = 0
        self.magnet_ads_used = 0
        self.hammer_ads_used = 0
        self.active_tool = "DROP"
        self.current_coin = self.get_random_coin()
        self.next_coin = self.get_random_coin()
        self.held_coin = None
        self.can_swap = True
        self.anim_coin = None
        self.merge_timer = 0
        self.pending_focus = None
        self.particles = []
        self.refresh_ui()

    def refresh_ui(self):
        self.score_lbl.text = f"Score: ${self.score}  |  Best: ${self.high_score}"
        self.btn_hold.text = f"HOLD\n{self.fmt_coin(self.held_coin)}"
        self.lbl_ready.text = f"READY\n{self.fmt_coin(self.current_coin)}"
        self.lbl_next.text = f"NEXT\n{self.fmt_coin(self.next_coin)}"

        if self.magnets_left > 0:
            self.btn_magnet.text = f"Magnet ({self.magnets_left})"
            self.btn_magnet.background_color = (0.15, 0.39, 0.92, 1)
        elif self.magnet_ads_used < self.max_booster_ads:
            self.btn_magnet.text = f"+1 Magnet (Ad {self.max_booster_ads - self.magnet_ads_used})"
            self.btn_magnet.background_color = (0.11, 0.30, 0.85, 1)
        else:
            self.btn_magnet.text = "Magnet (0)"
            self.btn_magnet.background_color = (0.28, 0.33, 0.41, 1)

        if self.hammers_left > 0:
            self.btn_hammer.text = f"Hammer ({self.hammers_left})"
            self.btn_hammer.background_color = (0.92, 0.35, 0.05, 1)
        elif self.hammer_ads_used < self.max_booster_ads:
            self.btn_hammer.text = f"+1 Hammer (Ad {self.max_booster_ads - self.hammer_ads_used})"
            self.btn_hammer.background_color = (0.76, 0.25, 0.05, 1)
        else:
            self.btn_hammer.text = "Hammer (0)"
            self.btn_hammer.background_color = (0.28, 0.33, 0.41, 1)

        self.btn_sound.text = "Sound: ON" if self.sound_on else "Sound: OFF"
        self.btn_sound.background_color = (0.09, 0.64, 0.29, 1) if self.sound_on else (0.28, 0.33, 0.41, 1)

        moves_left = 12 - self.dry_turns
        if self.active_tool == "HAMMER":
            self.status_lbl.text = "HAMMER ACTIVE: Tap any coin to smash!"
            self.status_lbl.color = (0.98, 0.57, 0.24, 1)
        elif self.current_coin == "2X":
            self.status_lbl.text = "2X READY: Tap column to DOUBLE / THAW!"
            self.status_lbl.color = (0.13, 0.83, 0.93, 1)
        elif moves_left <= 4:
            self.status_lbl.text = f"Merge soon! Row push in {moves_left} moves!"
            self.status_lbl.color = (0.96, 0.25, 0.37, 1)
        else:
            self.status_lbl.text = f"Tap column to drop  |  Push in {moves_left} moves"
            self.status_lbl.color = (0.22, 0.74, 0.97, 1)

    def update(self, dt):
        if self.modal_mode == "AD":
            self.ad_timer -= dt
            if self.ad_timer <= 0:
                cb = self.ad_callback
                self.modal_mode = None
                self.modal_box.opacity = 0
                self.modal_box.disabled = True
                self.play_sound("powerup")
                if cb:
                    cb()
            else:
                self.modal_desc.text = f"Ad ends in {max(1, math.ceil(self.ad_timer))}s..."
            return

        if self.anim_coin:
            self.anim_coin["y"] -= 28.0
            if self.anim_coin["y"] <= self.anim_coin["target_y"]:
                col, row, val = self.anim_coin["col"], self.anim_coin["row"], self.anim_coin["val"]
                self.grid[row][col] = val
                self.anim_coin = None
                if val == "2X":
                    self.dry_turns = 0
                    self.trigger_2x_coin(row, col)
                else:
                    self.play_sound("drop")
                    bx, by, _, _, cell = self.board_widget.get_cell_geometry()
                    draw_r = (self.rows - 1) - row
                    self.spawn_sparks(bx + (col + 0.5) * cell, by + (draw_r + 0.5) * cell - 15, (0.58, 0.64, 0.72), 6)
                    self.pulse_cell = (row, col)
                    self.pulse_timer = 8
                    self.pending_focus = (row, col)
                    self.merge_timer = 10
                self.refresh_ui()

        elif self.merge_timer > 0:
            self.merge_timer -= 1
            if self.merge_timer == 0 and self.pending_focus:
                self.step_merges()

        if self.shake_timer > 0:
            self.shake_timer -= 1
            self.shake_offset = (
                random.randint(-self.shake_intensity, self.shake_intensity),
                random.randint(-self.shake_intensity, self.shake_intensity)
            )
        else:
            self.shake_offset = (0, 0)

        if self.pulse_timer > 0:
            self.pulse_timer -= 1

        if self.particles:
            alive = []
            for p in self.particles:
                p["x"] += p["vx"]
                p["y"] += p["vy"]
                p["vy"] -= 0.25
                p["life"] -= 1
                if p["life"] > 0:
                    alive.append(p)
            self.particles = alive

        self.board_widget.redraw()


class CoinDrop3DApp(App):
    def build(self):
        return CoinDrop3DGame()


if __name__ == "__main__":
    CoinDrop3DApp().run()
