"""Interface language selection and translator management.

Language codes are stored in the preferences file under the "language" key.
The default, "en_US", means no translation is loaded and the built-in
English strings are shown. For any other language a compiled translation
file (not1mm_<language>.qm) must exist in the translations directory.

Translations use the standard Qt toolchain: .ts files are produced with
pylupdate6, translated, then compiled to .qm with lrelease. See the
translations/ directory.

Switching language does not require a restart. Windows and dialogs that were
built with load_ui() keep their generated Ui object so retranslate_all() can
re-apply the currently selected language to every open window.
"""

import logging
from pathlib import Path

from PyQt6 import QtCore, uic
from PyQt6.QtCore import QLibraryInfo, QTranslator
from PyQt6.QtWidgets import QApplication

from not1mm import fsutils

logger = logging.getLogger("i18n")

TRANSLATIONS_DIR = fsutils.APP_DATA_PATH / "translations"

# language code -> name shown in the settings dialog and Language menu.
SUPPORTED_LANGUAGES = {
    "en_US": "English",
    "de": "Deutsch",
    "es": "Español",
    "fr": "Français",
    "it": "Italiano",
    "ja": "日本語",
    "ko": "한국어",
    "pt_PT": "Português",
    "ru": "Русский",
    "zh_CN": "简体中文",
}

# QTranslator instances must outlive the strings they translate, so they are
# kept alive here for the life of the application.
_translators: list = []


def available_languages() -> list:
    """Return (code, name) pairs for every selectable interface language.

    English is always present as the built-in source language. The rest are
    gathered from the compiled translation files shipped in translations/.
    """
    languages = [("en_US", SUPPORTED_LANGUAGES["en_US"])]
    if TRANSLATIONS_DIR.is_dir():
        for path in sorted(TRANSLATIONS_DIR.glob("not1mm_*.qm")):
            code = path.stem[len("not1mm_") :]
            if code == "en_US":
                continue
            languages.append((code, SUPPORTED_LANGUAGES.get(code, code)))
    return languages


def install_language(app, language: str = "en_US") -> None:
    """Install (or remove) the translator for the requested language.

    Any previously installed translators are removed first, so switching the
    preference takes effect immediately for newly built widgets. Untranslated
    strings fall back to English. Qt's own translations are loaded when
    available so built-in widgets follow the chosen language too.
    """
    for translator in _translators:
        app.removeTranslator(translator)
    _translators.clear()

    if not language or language == "en_US":
        return

    app_translator = QTranslator()
    if app_translator.load(f"not1mm_{language}", str(TRANSLATIONS_DIR)):
        app.installTranslator(app_translator)
        _translators.append(app_translator)
        logger.info("Loaded interface translations for %s", language)

    qt_translations = Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath))
    qt_translator = QTranslator()
    if qt_translator.load(f"qt_{language}", str(qt_translations)):
        app.installTranslator(qt_translator)
        _translators.append(qt_translator)


def load_ui(widget, ui_file: Path) -> object:
    """Load a .ui file into *widget*.

    The UI is built with uic.loadUi exactly as the app always did, so every
    named widget is an attribute of *widget*. The generated Ui class is also
    retained on widget._ui so its retranslateUi() can be called later to
    apply a new interface language without rebuilding the window.
    """
    uic.loadUi(ui_file, widget)
    form_class, _ = uic.loadUiType(str(ui_file))
    form = form_class()
    for name in dir(widget):
        if name.startswith("_"):
            continue
        value = getattr(widget, name)
        if isinstance(value, QtCore.QObject):
            setattr(form, name, value)
    widget._ui = form
    return form


def retranslate_widget(widget) -> None:
    """Re-apply the current language to a widget built with load_ui()."""
    form = getattr(widget, "_ui", None)
    if form is not None and hasattr(form, "retranslateUi"):
        try:
            form.retranslateUi(widget)
        except AttributeError as exc:
            logger.warning("retranslateUi failed for %s: %s", widget.objectName(), exc)


def retranslate_all() -> None:
    """Re-apply the current language to every open top-level window."""
    app = QApplication.instance()
    if app is None:
        return
    for widget in app.topLevelWidgets():
        retranslate_widget(widget)
