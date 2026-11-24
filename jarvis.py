import ctypes, sys, math, os, re, random, asyncio, threading, subprocess, webbrowser, datetime, difflib, logging, tempfile, urllib.parse, urllib.request
import customtkinter as ctk
import speech_recognition as sr
import pyautogui
import pygame

try:
    import anthropic
except ImportError:
    anthropic = None

try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:
    genai = None

try:
    import edge_tts
except ImportError:
    edge_tts = None

os.chdir(os.path.dirname(sys.executable) if getattr(sys, "frozen", False)
         else os.path.dirname(os.path.abspath(__file__)))
logging.basicConfig(filename="log.txt", level=logging.ERROR,
                    format="%(asctime)s %(message)s", encoding="utf-8")

VOICE = "ru-RU-DmitryNeural"      # мужской голос
VOICE_F = "ru-RU-SvetlanaNeural"  # женский голос (переключатель в окне)
CITY = "Москва"                   # твой город для кнопки «Погода»

# Кнопки быстрых команд в окне: (надпись, что сказать Джарвису)
QUICK = [
    ("🌤 Погода", f"какая сейчас погода в городе {CITY}"),
    ("💵 Доллар", "сколько сейчас стоит доллар в рублях"),
    ("📰 Новости", "что самое важное произошло в мире сегодня"),
    ("▶ YouTube", "открой ютуб"), ("📸 Скриншот", "скриншот"),
    ("🔫 Rust", "открой раст"), ("🎯 CS2", "открой контр страйк"),
    ("🖼 Wallpaper", "открой wallpaper engine"),
    ("🔊 Громче", "громче"), ("🔉 Тише", "тише"),
]

# ---------- НЕЙРОСЕТЬ ----------
# Ключ берётся из файла key.txt (рядом с jarvis.py) или из переменной ANTHROPIC_API_KEY
MODEL = "claude-sonnet-5-5"          # если ключ от Anthropic (начинается с sk-ant)
GEMINI_MODEL = "gemini-flash-latest"  # если ключ от Google AI Studio (бесплатный)
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
if not API_KEY and os.path.exists("key.txt"):
    API_KEY = open("key.txt", encoding="utf-8").read().strip()
SYSTEM_PROMPT = (
    "Ты Джарвис, голосовой помощник на компьютере. Отвечай по-русски, тепло и просто, "
    "как живой человек, а не как робот. Твой ответ зачитывается вслух, поэтому: 1-3 коротких "
    "предложения, без списков, без markdown, без эмодзи, числа и валюты пиши словами или "
    "понятно на слух. Для погоды, курсов валют, новостей и всего свежего ищи в интернете. "
    "Если не уверен, так и скажи. Сегодня {date}."
)

# ---------- ТВОИ КОМАНДЫ: добавляй свои сюда ----------
SITES = {
    "ютуб": "https://youtube.com", "youtube": "https://youtube.com",
    "гугл": "https://google.com", "почту": "https://mail.google.com",
    "вк": "https://vk.com", "вконтакте": "https://vk.com",
    "телеграм веб": "https://web.telegram.org", "карты": "https://maps.google.com",
    "переводчик": "https://translate.google.com", "твич": "https://twitch.tv",
    "нетфликс": "https://netflix.com", "гитхаб": "https://github.com",
}
APPS = {
    "блокнот": "notepad", "калькулятор": "calc", "хром": "chrome",
    "браузер": "chrome", "проводник": "explorer", "диспетчер задач": "taskmgr",
    "настройки": "ms-settings:", "телеграм": "telegram", "стим": "steam",
    "дискорд": "discord", "ворд": "winword", "эксель": "excel",
    "пэйнт": "mspaint", "командную строку": "cmd",
}
# Игры из Steam запускаются через steam://rungameid/НОМЕР_ИГРЫ (нужен установленный Steam)
GAMES = {
    "раст": "steam://rungameid/252490", "rust": "steam://rungameid/252490",
    "контр страйк": "steam://rungameid/730", "counter-strike": "steam://rungameid/730",
    "counter strike": "steam://rungameid/730", "кс два": "steam://rungameid/730",
    "wallpaper engine": "steam://rungameid/431960", "обои": "steam://rungameid/431960",
    "дота": "steam://rungameid/570", "dota": "steam://rungameid/570",
    "гта": "steam://rungameid/271590", "апекс": "steam://rungameid/1172470",
    "террарию": "steam://rungameid/105600",
    # Игра не из Steam? Укажи путь к exe, например:
    # "майнкрафт": r"C:\Games\Minecraft\Minecraft.exe",
}
APPS.update(GAMES)

CLOSE = {"хром": "chrome.exe", "блокнот": "notepad.exe", "телеграм": "Telegram.exe",
         "стим": "steam.exe", "дискорд": "Discord.exe", "ворд": "WINWORD.EXE"}

OK = ["Да, пожалуйста.", "Да, конечно.", "Пожалуйста, уже открываю.", "Хорошо, сейчас сделаю.",
      "Конечно, уже делаю.", "Секунду.", "Без проблем.", "Сию минуту."]
NOT_UNDERSTOOD = ["Извини, не расслышал. Повтори, пожалуйста.",
                  "Хм, не понял. Скажи ещё раз.",
                  "Такой команды я пока не знаю."]


BG, CARD, CYAN = "#0b1020", "#131a33", "#00d4ff"
PAL = {"#888": "#5b6478", "#3ddc84": "#2ee6a6", "#f5a623": "#ffb020", "#4aa3ff": "#00d4ff"}


def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


HELP_TEXT = """ЗАЧЕМ ЭТО НУЖНО
Windows не позволяет программам выдавать права самим себе, поэтому нужно один раз проверить несколько вещей. Кнопки внизу откроют нужные окна и проверят результат. Это окно всегда можно открыть кнопкой «?» в углу.

1. МИКРОФОН (чтобы Джарвис тебя слышал)
• Нажми «Открыть настройки микрофона».
• Включи «Доступ к микрофону» и «Разрешить классическим приложениям доступ к микрофону».
• В Параметры → Система → Звук → Ввод выбери свой микрофон.
• Нажми «Проверить микрофон».

2. ИНТЕРНЕТ (для распознавания речи, ответов и голоса)
• При первом запуске Windows может спросить про брандмауэр для Python. Нажми «Разрешить доступ».
• Нажми «Проверить интернет».

3. УПРАВЛЕНИЕ ПРОГРАММАМИ, ГРОМКОСТЬЮ И ИГРАМИ
• Сайты, обычные программы, громкость и музыка работают без особых прав.
• Если нужное окно запущено от администратора (например, диспетчер задач или некоторые игры), Windows не пустит туда обычного Джарвиса. Тогда нажми «Запустить от администратора» и подтверди запрос Windows (UAC).
• Игры Джарвис только запускает. Внутри игр он ничего не нажимает.

4. STEAM (для запуска игр)
• Установи Steam и войди в аккаунт, затем нажми «Проверить Steam».

5. АНТИВИРУС
• Если антивирус блокирует Джарвиса, добавь папку с программой в исключения. Запускай только свои файлы.

Каждое разрешение подтверждаешь ты сам, Джарвис ничего не делает втайне."""


def make_client(key):
    """Ключ sk-ant... работает с Claude, любой другой считается ключом Google."""
    if not key:
        return None
    if key.startswith("sk-ant"):
        return anthropic.Anthropic(api_key=key) if anthropic else None
    return genai.Client(api_key=key) if genai else None


def pick(options):
    return random.choice(options)


def find_key(text, *dicts):
    """Ищет похожее название, даже если слово сказано не точно."""
    keys = {k: d[k] for d in dicts for k in d}
    for k in sorted(keys, key=len, reverse=True):
        if k in text:
            return k, keys[k]
    m = difflib.get_close_matches(text, list(keys), n=1, cutoff=0.6)
    return (m[0], keys[m[0]]) if m else (None, None)


def launch(target):
    subprocess.Popen(["cmd", "/c", "start", "", target], shell=False)


def key(name, times=1):
    for _ in range(times):
        pyautogui.press(name)


class Jarvis(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.title("Джарвис")
        self.geometry("600x920")
        self.minsize(560, 800)
        self.listening = False
        self.speaking = False
        self.history = []
        self.client = make_client(API_KEY)

        self.configure(fg_color=BG)
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(pady=(16, 0))
        ctk.CTkLabel(head, text="J.A.R.V.I.S", font=("Segoe UI", 24, "bold"), text_color=CYAN).pack()
        ctk.CTkLabel(head, text="твой голосовой помощник", font=("Segoe UI", 12), text_color="#6b7694").pack()

        c = self.orb = ctk.CTkCanvas(self, width=200, height=200, bg=BG, highlightthickness=0)
        c.pack(pady=(4, 0))
        c.create_oval(10, 10, 190, 190, outline="#16203f", width=2)
        self.rings = []
        for r, w in ((90, 3), (74, 4), (58, 3)):
            box = (100 - r, 100 - r, 100 + r, 100 + r)
            self.rings.append((c.create_arc(*box, start=0, extent=110, style="arc", width=w, outline="#5b6478"),
                               c.create_arc(*box, start=180, extent=110, style="arc", width=w, outline="#5b6478")))
        self.core = c.create_oval(72, 72, 128, 128, fill="#5b6478", outline="")
        self.orb_color, self.orb_on, self.phase = "#5b6478", False, 0

        self.status = ctk.CTkLabel(self, text="● Выключен", font=("Segoe UI", 15, "bold"), text_color="#5b6478",
                                   fg_color=CARD, corner_radius=16, width=190, height=32)
        self.status.pack(pady=(2, 10))
        self.btn = ctk.CTkButton(self, text="🎤  Включить Джарвиса", height=56, corner_radius=28,
                                 font=("Segoe UI", 17, "bold"), fg_color=CYAN, hover_color="#00a8cc",
                                 text_color="#001018", command=self.toggle)
        self.btn.pack(padx=28, pady=4, fill="x")

        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(padx=22, pady=(8, 4), fill="x")
        for i, (name, cmd) in enumerate(QUICK):
            grid.columnconfigure(i % 5, weight=1)
            ctk.CTkButton(grid, text=name.replace(" ", "\n", 1), height=58, corner_radius=14,
                          font=("Segoe UI Emoji", 12), fg_color=CARD, hover_color="#1d2850",
                          border_width=1, border_color="#22305f", text_color="#cfe8ff",
                          command=lambda c=cmd: self.run_text(c)
                          ).grid(row=i // 5, column=i % 5, padx=4, pady=4, sticky="ew")

        opts = ctk.CTkFrame(self, fg_color=CARD, corner_radius=14)
        opts.pack(padx=28, pady=6, fill="x")
        self.sw_voice = ctk.CTkSwitch(opts, text="Озвучка ответов", progress_color=CYAN)
        self.sw_wake = ctk.CTkSwitch(opts, text="Слово «Джарвис»", progress_color=CYAN)
        self.sw_female = ctk.CTkSwitch(opts, text="Женский голос", progress_color=CYAN)
        self.sw_top = ctk.CTkSwitch(opts, text="Поверх окон", progress_color=CYAN,
                                    command=lambda: self.attributes("-topmost", bool(self.sw_top.get())))
        self.sw_voice.select()
        self.sw_wake.select()
        for i, sw in enumerate((self.sw_voice, self.sw_wake, self.sw_female, self.sw_top)):
            sw.grid(row=i // 2, column=i % 2, padx=14, pady=7, sticky="w")
        ctk.CTkButton(opts, text="🔑 Ключ", width=84, height=32, corner_radius=16, fg_color="#22305f",
                      hover_color="#2d3f7a", command=self.set_key).grid(row=0, column=2, rowspan=2, padx=14)

        self.log = ctk.CTkScrollableFrame(self, fg_color="#0e1530", corner_radius=16)
        self.log.pack(padx=28, pady=8, fill="both", expand=True)
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(padx=28, pady=(0, 20), fill="x")
        self.entry = ctk.CTkEntry(row, placeholder_text="Или напиши команду и нажми Enter", height=44,
                                  corner_radius=22, fg_color=CARD, border_color="#22305f")
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", self.on_text)
        ctk.CTkButton(row, text="➤", width=44, height=44, corner_radius=22, fg_color=CYAN, hover_color="#00a8cc",
                      text_color="#001018", command=self.on_text).pack(side="left", padx=(8, 0))
        ctk.CTkButton(self, text="?", width=34, height=34, corner_radius=17, font=("Segoe UI", 16, "bold"),
                      fg_color=CARD, hover_color="#1d2850", border_width=1, border_color=CYAN, text_color=CYAN,
                      command=self.open_setup).place(relx=1.0, x=-14, y=14, anchor="ne")
        self.animate()

        pygame.mixer.init()
        self.rec = sr.Recognizer()
        self.rec.pause_threshold = 0.8
        self.say("Привет! Я Джарвис. Нажми кнопку, и я начну слушать.")
        if not os.path.exists("setup_done.flag"):
            self.after(700, lambda: self.open_setup(first=True))

    # ---------- интерфейс ----------
    def write(self, who, text):
        def _w():
            me = who == "Ты"
            line = ctk.CTkFrame(self.log, fg_color="transparent")
            line.pack(fill="x", pady=3)
            bub = ctk.CTkFrame(line, corner_radius=16, fg_color="#1f6aa5" if me else "#18264d",
                               border_width=0 if me else 1, border_color="#22407a")
            ctk.CTkLabel(bub, text=text, wraplength=330, justify="left", font=("Segoe UI", 14),
                         text_color="#ffffff" if me else "#d8f6ff").pack(padx=14, pady=9)
            bub.pack(side="right" if me else "left", padx=4)
            self.log.update_idletasks()
            self.log._parent_canvas.yview_moveto(1.0)
        self.after(0, _w)

    def set_status(self, text, color):
        def _s():
            c = PAL.get(color, color)
            self.status.configure(text=text, text_color=c)
            self.orb_color, self.orb_on = c, color != "#888"
        self.after(0, _s)

    def toggle(self):
        self.listening = not self.listening
        if self.listening:
            self.btn.configure(text="⏹ Выключить Джарвиса")
            self.set_status("● Слушаю...", "#3ddc84")
            threading.Thread(target=self.listen_loop, daemon=True).start()
        else:
            self.btn.configure(text="🎤 Включить Джарвиса")
            self.set_status("● Выключен", "#888")

    def on_text(self, _=None):
        text = self.entry.get().strip()
        self.entry.delete(0, "end")
        if text:
            self.run_text(text)

    # ---------- голос ----------
    def say(self, text):
        self.write("Джарвис", text)
        threading.Thread(target=self._speak, args=(text,), daemon=True).start()

    def _speak(self, text):
        if not self.sw_voice.get():
            return
        self.speaking = True
        self.set_status("● Говорю...", "#4aa3ff")
        try:
            if edge_tts is None:
                raise RuntimeError("edge-tts не установлен")
            path = os.path.join(tempfile.gettempdir(), f"jarvis_{random.randint(0, 99999)}.mp3")
            asyncio.run(edge_tts.Communicate(text, self.voice_name()).save(path))
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.wait(80)
            pygame.mixer.music.unload()
            os.remove(path)
        except Exception as e:
            logging.error(f"speak: {e}")
            try:
                import pyttsx3
                eng = pyttsx3.init()
                eng.say(text)
                eng.runAndWait()
            except Exception as e2:
                logging.error(f"pyttsx3: {e2}")
        finally:
            self.speaking = False
            self.idle_status()

    def listen_loop(self):
        try:
            with sr.Microphone() as mic:
                self.rec.adjust_for_ambient_noise(mic, duration=1)
                while self.listening:
                    if self.speaking:
                        pygame.time.wait(100)
                        continue
                    try:
                        audio = self.rec.listen(mic, timeout=3, phrase_time_limit=7)
                        text = self.rec.recognize_google(audio, language="ru-RU").lower()
                    except (sr.WaitTimeoutError, sr.UnknownValueError):
                        continue
                    except sr.RequestError:
                        self.say("Пропал интернет, не могу распознать речь.")
                        pygame.time.wait(3000)
                        continue
                    if "джарвис" in text or "джарвиз" in text or not self.sw_wake.get():
                        self.write("Ты", text)
                        cmd = re.sub(r"джарви[сз]\W*", "", text).strip()
                        if cmd:
                            self.handle(cmd)
                        else:
                            self.say("Слушаю тебя.")
        except Exception as e:
            logging.error(f"mic: {e}")
            self.say("Не получается включить микрофон. Проверь, что он подключён.")
            self.listening = False
            self.after(0, lambda: self.btn.configure(text="🎤 Включить Джарвиса"))
            self.set_status("● Выключен", "#888")

    # ---------- помощники интерфейса ----------
    def animate(self):
        self.phase += 0.07 if self.orb_on else 0.012
        col, c = self.orb_color, self.orb
        for i, (x, y) in enumerate(self.rings):
            st = math.degrees(self.phase) * (1.6 - i * 0.55) * (1 if i % 2 == 0 else -1)
            c.itemconfig(x, start=st, outline=col)
            c.itemconfig(y, start=st + 180, outline=col)
        r = 28 + (6 * math.sin(self.phase * 3) if self.orb_on else 0)
        c.coords(self.core, 100 - r, 100 - r, 100 + r, 100 + r)
        c.itemconfig(self.core, fill=col)
        self.after(33, self.animate)

    def run_text(self, text):
        self.write("Ты", text)
        threading.Thread(target=self.handle, args=(text.lower(),), daemon=True).start()

    def voice_name(self):
        return VOICE_F if self.sw_female.get() else VOICE

    def idle_status(self):
        if self.listening:
            self.set_status("● Слушаю...", "#3ddc84")
        else:
            self.set_status("● Выключен", "#888")

    def set_key(self):
        global API_KEY
        k = ctk.CTkInputDialog(text="Вставь ключ (Google AI Studio или Anthropic):", title="Ключ").get_input()
        if k and k.strip():
            API_KEY = k.strip()
            open("key.txt", "w", encoding="utf-8").write(API_KEY)
            self.client = make_client(API_KEY)
            self.say("Ключ сохранил. Теперь могу отвечать на любые вопросы.")

    def open_setup(self, first=False):
        win = ctk.CTkToplevel(self)
        win.title("Первый запуск: разрешения" if first else "Помощь и разрешения")
        win.geometry("540x720")
        win.attributes("-topmost", True)
        box = ctk.CTkTextbox(win, font=("Segoe UI", 13), wrap="word")
        box.pack(padx=16, pady=(16, 8), fill="both", expand=True)
        box.insert("1.0", HELP_TEXT)
        box.configure(state="disabled")
        res = ctk.CTkLabel(win, text=f"Права администратора: {'есть' if is_admin() else 'нет'}",
                           wraplength=490, justify="left")
        res.pack(padx=16, pady=4, anchor="w")

        def show(t):
            res.configure(text=t)

        def mic():
            try:
                with sr.Microphone() as m:
                    sr.Recognizer().adjust_for_ambient_noise(m, duration=0.5)
                show("Микрофон работает.")
            except Exception as e:
                logging.error(f"mic test: {e}")
                show("Микрофон не отвечает. Проверь шаг 1 и выбери нужный микрофон в настройках звука.")

        def net():
            try:
                urllib.request.urlopen("https://www.google.com", timeout=5)
                show("Интернет есть.")
            except Exception:
                show("Нет доступа в интернет. Проверь соединение и брандмауэр (шаг 2).")

        def steam():
            try:
                import winreg
                winreg.CloseKey(winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "steam"))
                show("Steam найден, игры будут запускаться.")
            except Exception:
                show("Steam не найден. Установи его и войди в аккаунт (шаг 4).")

        def admin():
            frozen = getattr(sys, "frozen", False)
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable,
                                                None if frozen else f'"{os.path.abspath(__file__)}"',
                                                os.getcwd(), 1)
            self.after(300, self.destroy)

        def done():
            open("setup_done.flag", "w").write("ok")
            win.destroy()

        buttons = [("Открыть настройки микрофона", lambda: os.startfile("ms-settings:privacy-microphone")),
                   ("Проверить микрофон", mic), ("Проверить интернет", net), ("Проверить Steam", steam),
                   ("Запустить от администратора", admin), ("Готово", done)]
        grid = ctk.CTkFrame(win, fg_color="transparent")
        grid.pack(padx=16, pady=(4, 16), fill="x")
        for i, (t, f) in enumerate(buttons):
            grid.columnconfigure(i % 2, weight=1)
            ctk.CTkButton(grid, text=t, command=f, fg_color="#1f6aa5" if t == "Готово" else "#2b2b3d"
                          ).grid(row=i // 2, column=i % 2, padx=4, pady=4, sticky="ew")
        win.after(200, win.lift)

    # ---------- команды ----------
    def handle(self, t):
        try:
            self._handle(t)
        except Exception as e:
            logging.error(f"command '{t}': {e}")
            self.say("Что-то пошло не так, но я продолжаю работать.")

    def _handle(self, t):
        # время и дата
        if "который час" in t or "сколько времени" in t or t.strip() == "время":
            return self.say(datetime.datetime.now().strftime("Сейчас %H:%M."))
        if "какое число" in t or "какая дата" in t or "какой сегодня день" in t:
            return self.say(datetime.datetime.now().strftime("Сегодня %d.%m.%Y."))

        # громкость и музыка
        if "громче" in t:
            key("volumeup", 6); return self.say(pick(OK))
        if "тише" in t:
            key("volumedown", 6); return self.say(pick(OK))
        if "без звука" in t or "выключи звук" in t:
            key("volumemute"); return self.say(pick(OK))
        if t in ("пауза", "поставь на паузу", "играй", "продолжи", "включи музыку"):
            key("playpause"); return self.say(pick(OK))
        if "следующ" in t:
            key("nexttrack"); return self.say(pick(OK))
        if "предыдущ" in t:
            key("prevtrack"); return self.say(pick(OK))

        # скриншот
        if "скриншот" in t:
            name = datetime.datetime.now().strftime("screenshot_%H%M%S.png")
            pyautogui.screenshot(name)
            return self.say(f"Сделал скриншот, файл {name} лежит рядом с программой.")

        # таймер
        m = re.search(r"таймер.*?(\d+)\s*(секунд|сек|минут|мин)", t)
        if m:
            n = int(m.group(1))
            sec = n * (60 if m.group(2).startswith("мин") else 1)
            threading.Timer(sec, lambda: self.say("Время вышло!")).start()
            return self.say(f"Хорошо, поставил таймер на {n} {m.group(2)}.")

        # система
        if "заблокируй" in t:
            self.say("Блокирую."); return subprocess.Popen("rundll32.exe user32.dll,LockWorkStation")
        if "отмени выключение" in t or "отмена выключения" in t:
            subprocess.Popen("shutdown /a", shell=True); return self.say("Отменил.")
        if "выключи компьютер" in t:
            subprocess.Popen("shutdown /s /t 30", shell=True)
            return self.say("Выключаю через тридцать секунд. Чтобы отменить, скажи: отмени выключение.")
        if "перезагрузи" in t:
            subprocess.Popen("shutdown /r /t 30", shell=True)
            return self.say("Перезагружаю через тридцать секунд. Скажи «отмени выключение», если передумаешь.")

        # закрыть программу
        if t.startswith(("закрой", "закрыть")):
            k, exe = find_key(re.sub(r"^закрой(те)?|^закрыть", "", t).strip(), CLOSE)
            if exe:
                subprocess.Popen(f"taskkill /im {exe} /f", shell=True)
                return self.say(pick(OK))
            return self.say("Не знаю, как закрыть эту программу.")

        # поиск
        m = re.search(r"(?:найди|поищи|загугли)\s+(.+)", t)
        if m:
            q = urllib.parse.quote(m.group(1).replace("в ютубе", "").replace("в youtube", "").strip())
            if "ютуб" in t or "youtube" in t:
                webbrowser.open(f"https://www.youtube.com/results?search_query={q}")
            else:
                webbrowser.open(f"https://www.google.com/search?q={q}")
            return self.say("Вот, что нашёл.")

        # открыть сайт или программу
        if t.startswith(("открой", "запусти", "включи", "открыть", "зайди")):
            name = re.sub(r"^(открой|запусти|включи|открыть|зайди на|зайди в|зайди)\s*", "", t).strip()
            k, target = find_key(name, SITES, APPS)
            if target:
                self.say(pick(OK))
                return webbrowser.open(target) if target.startswith("http") else launch(target)
            return self.say("Не нашёл такое у себя в списке. Добавь его в начало файла jarvis.py.")

        # прощание
        if t in ("пока", "стоп", "выключись", "отдыхай"):
            self.say("Хорошо, отдыхаю. Зови, если что.")
            self.listening = False
            self.after(0, lambda: self.btn.configure(text="🎤 Включить Джарвиса"))
            return self.set_status("● Выключен", "#888")

        if "привет" in t:
            return self.say("Привет! Чем могу помочь?")
        if "как дела" in t:
            return self.say("Всё отлично, спасибо что спросил. Что открыть?")
        if "спасибо" in t:
            return self.say("Всегда пожалуйста.")

        self.ask_ai(t)

    def ask_gemini(self, system):
        msgs = [{"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]}
                for m in self.history[-12:]]
        cfg = genai_types.GenerateContentConfig(
            system_instruction=system,
            tools=[genai_types.Tool(google_search=genai_types.GoogleSearch())])
        try:
            r = self.client.models.generate_content(model=GEMINI_MODEL, contents=msgs, config=cfg)
        except Exception as e:  # если поиск недоступен, отвечаем без него
            logging.error(f"gemini search: {e}")
            cfg = genai_types.GenerateContentConfig(system_instruction=system)
            r = self.client.models.generate_content(model=GEMINI_MODEL, contents=msgs, config=cfg)
        return (r.text or "").strip()

    def ask_ai(self, question):
        """Любой вопрос уходит нейросети; для свежих данных она сама ищет в интернете."""
        if not self.client:
            return self.say("Чтобы отвечать на любые вопросы, мне нужен ключ нейросети. "
                            "Положи его в файл key.txt рядом с программой.")
        self.set_status("● Думаю...", "#f5a623")
        try:
            self.history.append({"role": "user", "content": question})
            system = SYSTEM_PROMPT.format(date=datetime.date.today().strftime("%d.%m.%Y"))
            if API_KEY.startswith("sk-ant"):
                resp = self.client.messages.create(
                    model=MODEL, max_tokens=600, system=system,
                    messages=self.history[-12:],
                    tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}],
                )
                answer = " ".join(x.text for x in resp.content if x.type == "text").strip()
            else:
                answer = self.ask_gemini(system)
            answer = re.sub(r"[*#_`]", "", answer) or pick(NOT_UNDERSTOOD)
            self.history.append({"role": "assistant", "content": answer})
            self.say(answer)
        except Exception as e:
            logging.error(f"ai: {e}")
            if self.history and self.history[-1]["role"] == "user":
                self.history.pop()
            self.say("Не получилось получить ответ. Проверь интернет и ключ нейросети.")
        finally:
            if self.listening:
                self.set_status("● Слушаю...", "#3ddc84")
            else:
                self.set_status("● Выключен", "#888")


if __name__ == "__main__":
    pyautogui.FAILSAFE = False
    Jarvis().mainloop()
