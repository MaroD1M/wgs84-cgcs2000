(function () {
    'use strict';

    const MOBILE_QUERY = '(max-width: 767.98px), (max-width: 1023.98px) and (max-height: 500px) and (pointer: coarse)';
    const mql = window.matchMedia(MOBILE_QUERY);
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    let logCollapsed = false;

    function isMobile() {
        return mql.matches;
    }

    function scrollToElement(el) {
        if (!el || el.classList.contains('d-none')) return;
        el.scrollIntoView({
            behavior: reduceMotion.matches ? 'auto' : 'smooth',
            block: 'start',
        });
    }

    function setLogCollapsed(collapsed) {
        const box = document.getElementById('log-box');
        const btn = document.getElementById('log-toggle');
        if (!box || !btn) return;
        logCollapsed = collapsed;
        box.classList.toggle('is-collapsed', collapsed);
        btn.textContent = collapsed ? '展开日志' : '收起日志';
        btn.setAttribute('aria-expanded', String(!collapsed));
    }

    function initLog() {
        const btn = document.getElementById('log-toggle');
        if (btn) {
            btn.addEventListener('click', () => {
                setLogCollapsed(!logCollapsed);
            });
        }

        const box = document.getElementById('log-box');
        if (box && window.MutationObserver) {
            const observer = new MutationObserver(() => {
                if (!isMobile() || !logCollapsed) return;
                const last = box.lastElementChild;
                if (last && last.querySelector('.log-err')) {
                    setLogCollapsed(false);
                }
            });
            observer.observe(box, { childList: true });
        }

        setLogCollapsed(isMobile());
    }

    function initMapCheckboxes() {
        [
            ['s-mapEnabled', 's-map'],
            ['b-mapEnabled', 'b-map'],
        ].forEach(([checkboxId, mapId]) => {
            const checkbox = document.getElementById(checkboxId);
            if (!checkbox) return;
            checkbox.addEventListener('change', () => {
                if (!isMobile() || !checkbox.checked) return;
                window.setTimeout(() => scrollToElement(document.getElementById(mapId)), 260);
            });
        });
    }

    function invalidateMaps() {
        if (typeof window.invalidateAppMaps === 'function') {
            window.invalidateAppMaps();
        }
    }

    function initViewportListeners() {
        let timer = null;
        const refresh = () => {
            if (!isMobile()) return;
            window.clearTimeout(timer);
            timer = window.setTimeout(invalidateMaps, 180);
        };
        window.addEventListener('orientationchange', refresh);
        window.addEventListener('resize', refresh);
    }

    function handleBreakpointChange() {
        setLogCollapsed(isMobile());
        if (isMobile()) {
            window.setTimeout(invalidateMaps, 180);
        }
    }

    function afterSingleSuccess() {
        if (!isMobile()) return;
        scrollToElement(document.getElementById('s-result'));
    }

    function afterBatchSuccess() {
        if (!isMobile()) return;
        const summary = document.getElementById('b-summary');
        const target = summary && !summary.classList.contains('d-none')
            ? summary
            : document.querySelector('#tab-batch .tbl-wrap');
        scrollToElement(target);
    }

    function init() {
        initLog();
        initMapCheckboxes();
        initViewportListeners();
        if (mql.addEventListener) {
            mql.addEventListener('change', handleBreakpointChange);
        } else if (mql.addListener) {
            mql.addListener(handleBreakpointChange);
        }
    }

    window.MobileEnhance = {
        isMobile,
        afterSingleSuccess,
        afterBatchSuccess,
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
