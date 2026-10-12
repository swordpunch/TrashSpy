"""TrashSpy UI translations: ru / uk / en / be / kk."""
import json
import os
from pathlib import Path

CODES = ["ru", "uk", "en", "be", "kk"]
NAMES = ["Русский", "Українська", "English", "Беларуская", "Қазақша"]

STRINGS = {
"tab_history": ["История удалений", "Історія видалень", "Deletion history",
                "Гісторыя выдаленняў", "Жою тарихы"],
"tab_recent": ["Недавно удалённые", "Нещодавно видалені", "Recently deleted",
               "Нядаўна выдаленыя", "Жақында жойылғандар"],
"hist_info": ["Журнал ведется с момента запуска слежения (кнопка ниже) "
              "и только пока программа запущена.",
              "Журнал ведеться з моменту запуску стеження (кнопка нижче) "
              "і лише доки програма запущена.",
              "Log is kept from the moment you start watching (button below) "
              "and only while the app is running.",
              "Журнал вядзецца з моманту запуску сачэння (кнопка ніжэй) "
              "і толькі пакуль праграма запушчана.",
              "Журнал бақылауды іске қосқаннан кейін (төмендегі батырма) "
              "және бағдарлама жұмыс істеп тұрғанда ғана жүргізіледі."],
"btn_add_watch": ["Добавить папку для слежения", "Додати папку для стеження",
                  "Watch a folder", "Дадаць папку для сачэння", "Бақылауға папка қосу"],
"btn_refresh": ["Обновить", "Оновити", "Refresh", "Абнавіць", "Жаңарту"],
"btn_clear_hist": ["Очистить историю", "Очистити історію", "Clear history",
                   "Ачысціць гісторыю", "Тарихты тазалау"],
"btn_open_folder": ["Открыть папку", "Відкрити папку", "Open folder",
                    "Адкрыць папку", "Папканы ашу"],
"watch_none": ["Слежение: нет", "Стеження: нема", "Watching: none",
               "Сачэнне: няма", "Бақылау: жоқ"],
"watch_fmt": ["Слежение: {x}", "Стеження: {x}", "Watching: {x}",
              "Сачэнне: {x}", "Бақылау: {x}"],
"col_name": ["Имя", "Ім'я", "Name", "Імя", "Атауы"],
"col_deleted": ["Удален", "Видалено", "Deleted", "Выдалены", "Жойылған"],
"col_path": ["Был путь", "Був шлях", "Was at", "Быў шлях", "Болған жолы"],
"col_watched": ["Папка слежения", "Папка стеження", "Watched folder",
                "Папка сачэння", "Бақыланатын папка"],
"col_drive": ["Том", "Том", "Drive", "Том", "Том"],
"first_scan": ["Первое сканирование…", "Перше сканування…", "First scan…",
               "Першае сканаванне…", "Алғашқы сканерлеу…"],
"recent_info": ["Удаления за последние дни/недели из журнала NTFS. "
                "Стежение не нужно, но нужен запуск от администратора.",
                "Видалення за останні дні/тижні з журналу NTFS. "
                "Стеження не потрібне, але потрібен запуск від адміністратора.",
                "Deletions from the last days/weeks, from the NTFS journal. "
                "No watching needed, but must run as administrator.",
                "Выдаленні за апошнія дні/тыдні з журнала NTFS. "
                "Сачэнне не патрэбна, але патрэбен запуск ад адміністратара.",
                "NTFS журналынан соңғы күндер/апталардағы жоюлар. "
                "Бақылау қажет емес, бірақ әкімші ретінде іске қосу керек."],
"btn_scan": ["Сканировать", "Сканувати", "Scan", "Сканаваць", "Сканерлеу"],
"btn_run_admin": ["Запустить от администратора", "Запустити від адміністратора",
                  "Restart as administrator", "Запусціць ад адміністратара",
                  "Әкімші ретінде іске қосу"],
"lang_label": ["Язык:", "Мова:", "Language:", "Мова:", "Тіл:"],
"dlg_choose_dir": ["Выбери папку для слежения", "Вибери папку для стеження",
                   "Choose a folder to watch", "Выберы папку для сачэння",
                   "Бақылауға папка таңда"],
"dlg_confirm": ["Подтверждение", "Підтвердження", "Confirm",
                "Пацверджанне", "Растау"],
"ask_clear_hist": ["Очистить историю?", "Очистити історію?", "Clear history?",
                   "Ачысціць гісторыю?", "Тарихты тазалау керек пе?"],
"admin_launched": ["Запускаю копию от администратора. Это окно можно закрыть.",
                   "Запускаю копію від адміністратора. Це вікно можна закрити.",
                   "Starting a copy as administrator. You can close this window.",
                   "Запускаю копію ад адміністратара. Гэта акно можна закрыць.",
                   "Әкімші ретінде көшірме іске қосылуда. Бұл терезені жабуға болады."],
"err_admin_fail": ["Не получилось запросить права.", "Не вдалося запитати права.",
                   "Could not request privileges.", "Не ўдалося запытаць правы.",
                   "Құқықтар сұрау сәтсіз болды."],
"err_title": ["Ошибка", "Помилка", "Error", "Памылка", "Қате"],
"pick_row": ["Выбери строку в списке.", "Вибери рядок у списку.",
             "Select a row in the list.", "Выберы радок у спісе.",
             "Тізімнен жол таңда."],
"folder_gone": ["Папка уже не существует:\n{path}", "Папки вже не існує:\n{path}",
                "Folder no longer exists:\n{path}", "Папкі ўжо не існуе:\n{path}",
                "Папка енді жоқ:\n{path}"],
"need_admin_title": ["Нужен администратор", "Потрібен адміністратор",
                     "Administrator needed", "Патрэбен адміністратар",
                     "Әкімші қажет"],
"scan_perm": ["Запусти TrashSpy от имени администратора: правый клик → "
              "Запуск от имени администратора.",
              "Запусти TrashSpy від адміністратора: правий клік → "
              "Запуск від адміністратора.",
              "Run TrashSpy as administrator: right click → Run as administrator.",
              "Запусці TrashSpy ад адміністратара: правы клік → "
              "Запуск ад адміністратара.",
              "TrashSpy-ді әкімші ретінде іске қос: оң жақ батырма → "
              "Әкімші ретінде іске қосу."],
"status_check": ["Проверка: {w} …", "Перевірка: {w} …", "Checking: {w} …",
                 "Праверка: {w} …", "Тексеру: {w} …"],
"status_watching": ["Под наблюдением: {w} ({n} файлов/папок)",
                    "Під наглядом: {w} ({n} файлів/папок)",
                    "Watching: {w} ({n} files/folders)",
                    "Пад наглядам: {w} ({n} файлаў/папак)",
                    "Бақылауда: {w} ({n} файл/папка)"],
"scanning": ["Сканирование…", "Сканування…", "Scanning…",
             "Сканаванне…", "Сканерлеу…"],
"found_fmt": ["Найдено удалений: {n}", "Знайдено видалень: {n}",
              "Deletions found: {n}", "Знойдзена выдаленняў: {n}",
              "Жоюлар табылды: {n}"],
"no_drives": ["NTFS-томы не найдены.", "NTFS-томи не знайдено.",
              "No NTFS volumes found.", "NTFS-тамы не знойдзены.",
              "NTFS томдары табылмады."],
"vol_open_fail": ["не открыт том {L}: (нужны права администратора)",
                  "не відкрито том {L}: (потрібні права адміністратора)",
                  "cannot open volume {L}: (administrator rights needed)",
                  "не адкрыты том {L}: (патрэбны правы адміністратара)",
                  "{L} томы ашылмады: (әкімші құқығы қажет)"],
"vol_no_usn": ["на томе {L}: нет журнала USN",
               "на томі {L}: нема журналу USN",
               "volume {L}: no USN journal",
               "на томе {L}: няма журнала USN",
               "{L} томында USN журналы жоқ"],
"vol_mft_err": ["ошибка чтения MFT тома {L}", "помилка читання MFT тому {L}",
                "error reading MFT of volume {L}", "памылка чытання MFT тома {L}",
                "{L} томының MFT оқу қатесі"],
"vol_journal_err": ["ошибка чтения журнала тома {L}",
                    "помилка читання журналу тому {L}",
                    "error reading journal of volume {L}",
                    "памылка чытання журнала тома {L}",
                    "{L} томының журналын оқу қатесі"],
"map_progress": ["Том {L}: построение карты файлов… {n}",
                 "Том {L}: побудова карти файлів… {n}",
                 "Volume {L}: building file map… {n}",
                 "Том {L}: пабудова карты файлаў… {n}",
                 "{L} томы: файл картасын құру… {n}"],
"journal_progress": ["Том {L}: чтение журнала… {n} удалений",
                     "Том {L}: читання журналу… {n} видалень",
                     "Volume {L}: reading journal… {n} deletions",
                     "Том {L}: чытанне журнала… {n} выдаленняў",
                     "{L} томы: журналды оқу… {n} жою"],
"search_ph": ["Поиск по имени или пути…", "Пошук за ім'ям або шляхом…",
              "Search by name or path…", "Пошук па імені ці шляху…",
              "Атауы немесе жолы бойынша іздеу…"],
"shown_fmt": ["Показано: {n}", "Показано: {n}", "Shown: {n}",
              "Паказана: {n}", "Көрсетілді: {n}"],
"btn_clear": ["Очистить", "Очистити", "Clear", "Ачысціць", "Тазалау"],
}

_current = "ru"


def _config_path():
    base = os.environ.get("APPDATA") or str(Path.home())
    d = Path(base) / "TrashSpy"
    d.mkdir(parents=True, exist_ok=True)
    return d / "config.json"


def app_dir():
    base = os.environ.get("APPDATA") or str(Path.home())
    d = Path(base) / "TrashSpy"
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_lang() -> str:
    global _current
    try:
        code = json.loads(_config_path().read_text(encoding="utf-8")).get("lang", "ru")
        if code in CODES:
            _current = code
    except Exception:
        pass
    return _current


def save_lang(code: str):
    global _current
    _current = code
    try:
        _config_path().write_text(json.dumps({"lang": code}), encoding="utf-8")
    except Exception:
        pass


def get_lang() -> str:
    return _current


def S(key: str, **kw) -> str:
    try:
        idx = CODES.index(_current)
    except ValueError:
        idx = 0
    vals = STRINGS.get(key, [key])
    text = vals[idx] if idx < len(vals) else vals[0]
    try:
        return text.format(**kw)
    except Exception:
        return text


load_lang()
