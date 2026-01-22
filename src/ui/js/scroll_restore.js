// Scroll utilities: get current scroll ratio and set scroll by ratio
// getScrollRatio(): returns a number between 0 and 1
// setScrollRatio(ratio): scrolls to the given ratio (0..1) and returns the final y offset

function getScrollRatio() {
    try {
        var h = document.documentElement.scrollHeight || document.body.scrollHeight;
        var win = window.innerHeight || document.documentElement.clientHeight;
        var y = window.scrollY || window.pageYOffset || 0;
        var ratio = (h - win > 0) ? (y / (h - win)) : 0;
        return ratio;
    } catch (e) {
        return 0;
    }
}

function setScrollRatio(ratio) {
    try {
        ratio = Math.max(0, Math.min(1, Number(ratio) || 0));
        var h = document.documentElement.scrollHeight || document.body.scrollHeight;
        var win = window.innerHeight || document.documentElement.clientHeight;
        var y = 0;
        if (h - win > 0) y = Math.round(ratio * (h - win));
        window.scrollTo(0, y);
        return y;
    } catch (e) {
        return 0;
    }
}
