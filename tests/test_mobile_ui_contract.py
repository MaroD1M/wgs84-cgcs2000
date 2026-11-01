from pathlib import Path

from main import app

ROOT = Path(__file__).resolve().parents[1]
HTML = app.test_client().get("/").get_data(as_text=True)
CSS = (ROOT / "static" / "css" / "mobile.css").read_text()
JS = (ROOT / "static" / "js" / "mobile.js").read_text()
TEMPLATE = (ROOT / "templates" / "index.html").read_text()


def test_mobile_assets_load_after_inline_styles():
    assert "viewport-fit=cover" in HTML
    assert '/static/css/mobile.css' in HTML
    assert '/static/js/mobile.js' in HTML
    assert HTML.index('/static/css/mobile.css') > HTML.index('</style>')
    assert HTML.index('/static/js/mobile.js') > HTML.index('id="mainTabs"')


def test_mobile_markup_hooks_exist():
    assert HTML.count('class="tab-full"') == 3
    assert HTML.count('class="tab-short"') == 3
    assert HTML.count('crs-row') == 2
    assert 'mobile-card-table batch-card-table' in HTML
    assert 'mobile-card-table dms-card-table' in HTML
    assert 'id="log-toggle"' in HTML
    assert 'data-label="输入数据"' in HTML
    assert 'data-label="输出结果"' in HTML
    assert 'data-label="备注 / 错误"' in HTML
    assert 'role="status" aria-live="polite"' in HTML
    assert 'class="mobile-help d-md-none"' in HTML


def test_mobile_css_is_scoped_and_covers_touch_layout():
    assert '@media (max-width: 767.98px)' in CSS
    assert '@media (max-width: 359.98px)' in CSS
    assert '(max-height: 500px) and (pointer: coarse)' in CSS
    assert '--mobile-touch: 46px' in CSS
    assert 'min-height: var(--mobile-touch)' in CSS
    assert 'font-size: 1rem' in CSS
    assert '.mobile-card-table thead' in CSS
    assert '.batch-card-table td[data-label="输出结果"]' in CSS
    assert '.dms-card-table td[data-label="结果"]' in CSS
    assert 'env(safe-area-inset-bottom)' in CSS


def test_mobile_js_is_gated_and_wires_enhancements():
    assert "matchMedia(MOBILE_QUERY)" in JS
    assert 'function isMobile()' in JS
    assert 'return mql.matches;' in JS
    assert 'afterSingleSuccess' in JS
    assert 'afterBatchSuccess' in JS
    assert 'MutationObserver' in JS
    assert 'invalidateAppMaps' in JS
    assert 'is-collapsed' in JS


def test_tianditu_settings_panel_exists():
    assert 'id="mapSettings"' in HTML
    assert 'window.APP_VERSION' in HTML
    assert '应用版本：' in HTML
    assert 'id="tianditu-key-input"' in HTML
    assert 'id="tianditu-key-save"' in HTML
    assert 'id="tianditu-key-clear"' in HTML
    assert "TIANDITU_KEY_STORAGE" in TEMPLATE
    assert 'map-settings-offcanvas' in CSS
    assert '.map-warning' in TEMPLATE


def test_only_tianditu_provider_remains():
    assert "OpenStreetMap" not in TEMPLATE
    assert "MAP_TILE_URL" not in TEMPLATE
    assert "OSM_TILE_URL" not in TEMPLATE
    assert "provider === 'osm'" not in TEMPLATE
    assert "provider === 'custom'" not in TEMPLATE


def test_form_labels_reference_existing_controls():
    from html.parser import HTMLParser

    class LabelParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.ids = set()
            self.for_ids = []
            self.labels_without_for = 0

        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if "id" in attrs:
                self.ids.add(attrs["id"])
            if tag == "label":
                if "for" in attrs:
                    self.for_ids.append(attrs["for"])
                else:
                    self.labels_without_for += 1

    parser = LabelParser()
    parser.feed(HTML)
    assert all(for_id in parser.ids for for_id in parser.for_ids)
    assert parser.labels_without_for == 1
