// Mouse handler for reading mode
// Loads Qt WebChannel and forwards left/right mouse clicks to Python bridge

document.addEventListener('DOMContentLoaded', function() {
    new QWebChannel(qt.webChannelTransport, function(channel) {
        window.bridge = channel.objects.bridge;
    });
});

// Ignore clicks on the scrollbar area (prevent page turning when the scrollbar is clicked)
document.addEventListener('mousedown', function(e) {
    try {
        var scrollbarWidth = window.innerWidth - (document.documentElement.clientWidth || document.body.clientWidth || 0);
        // If computed scrollbar width > 0 and click is within the scrollbar area on the right, ignore the event
        if (scrollbarWidth > 0 && e.clientX >= window.innerWidth - scrollbarWidth) {
            return;
        }
    } catch (err) {
        // On error, do not interfere with normal click handling
    }

    // Ignore clicks on editable input controls
    var tgt = e.target;
    if (tgt && (tgt.tagName === 'INPUT' || tgt.tagName === 'TEXTAREA' || tgt.isContentEditable)) {
        return;
    }

    if (window.bridge) {
        if (e.button === 0) window.bridge.onMouseClick('left');
        else if (e.button === 2) window.bridge.onMouseClick('right');
    }
});

document.addEventListener('contextmenu', function(e) { e.preventDefault(); });
