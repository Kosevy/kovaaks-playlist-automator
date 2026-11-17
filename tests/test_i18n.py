import unittest
from core.i18n import t, get_i18n, detect_system_language, TRANSLATIONS


class TestI18n(unittest.TestCase):

    def setUp(self):
        self.i18n = get_i18n()
        self.original_lang = self.i18n.language

    def tearDown(self):
        self.i18n.set_language(self.original_lang)

    def _get_all_keys(self, d, prefix=""):
        keys = set()
        for k, v in d.items():
            full_key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                keys.update(self._get_all_keys(v, full_key))
            else:
                keys.add(full_key)
        return keys

    def test_key_parity_between_es_and_en(self):
        """Verifica que el 100% de las claves en español existan en inglés y viceversa."""
        es_keys = self._get_all_keys(TRANSLATIONS["es"])
        en_keys = self._get_all_keys(TRANSLATIONS["en"])

        missing_in_en = es_keys - en_keys
        missing_in_es = en_keys - es_keys

        self.assertEqual(
            missing_in_en,
            set(),
            f"Claves presentes en 'es' pero ausentes en 'en': {missing_in_en}"
        )
        self.assertEqual(
            missing_in_es,
            set(),
            f"Claves presentes en 'en' pero ausentes en 'es': {missing_in_es}"
        )

    def test_translation_and_formatting(self):
        """Prueba la traducción y la interpolación de parámetros en ambos idiomas."""
        # Probar español
        self.i18n.set_language("es")
        self.assertEqual(self.i18n.language, "es")
        title_es = t("header.title")
        self.assertIn("KPA", title_es)

        delta_es = t("overlays.delta_points", delta="350.0")
        self.assertEqual(delta_es, "+350.0 pts")

        pts_es = t("overlays.points_remaining", points="120.0", next_rank="Cerulean")
        self.assertIn("Faltan 120.0 pts para Cerulean", pts_es)

        # Probar inglés
        self.i18n.set_language("en")
        self.assertEqual(self.i18n.language, "en")
        self.assertEqual(t("tabs.generator"), "⚡ Playlist Generator")

        delta_en = t("overlays.delta_points", delta="350.0")
        self.assertEqual(delta_en, "+350.0 pts")

        pts_en = t("overlays.points_remaining", points="120.0", next_rank="Cerulean")
        self.assertIn("120.0 pts remaining for Cerulean", pts_en)

    def test_listener_notification_on_language_change(self):
        """Verifica que los observadores registrados sean notificados al cambiar de idioma."""
        notifications = []

        def callback():
            notifications.append(self.i18n.language)

        self.i18n.register_listener(callback)
        self.i18n.set_language("es")
        self.i18n.set_language("en")
        self.assertIn("en", notifications)

        # Limpiar
        self.i18n.unregister_listener(callback)
        notifications.clear()
        self.i18n.set_language("es")
        self.assertEqual(len(notifications), 0)

    def test_detect_system_language(self):
        """Verifica que la detección del sistema retorne un código válido ('es' o 'en')."""
        lang = detect_system_language()
        self.assertIn(lang, ("es", "en"))


if __name__ == "__main__":
    unittest.main()
