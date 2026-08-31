import objc
import threading
from AppKit import (
    NSPanel, NSView, NSColor, NSBezierPath, NSScreen, NSTimer,
    NSMakeRect, NSFont, NSAttributedString, NSMutableParagraphStyle,
    NSFontAttributeName, NSForegroundColorAttributeName,
    NSParagraphStyleAttributeName, NSCenterTextAlignment,
    NSNonactivatingPanelMask, NSBorderlessWindowMask,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorStationary,
    NSWindowCollectionBehaviorIgnoresCycle,
)

_PANEL_W = 220
_PANEL_H = 52
_DOT_R = 7
_CORNER = 14


class _RecordingView(NSView):

    @objc.python_method
    def _setup(self):
        self._alpha = 1.0
        self._fading_in = False

    def drawRect_(self, rect):
        # Pill background
        NSColor.colorWithCalibratedRed_green_blue_alpha_(0.1, 0.1, 0.1, 0.92).set()
        pill = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
            NSMakeRect(0, 0, _PANEL_W, _PANEL_H), _CORNER, _CORNER
        )
        pill.fill()

        # Pulsing red dot
        cx = 20 + _DOT_R
        cy = _PANEL_H / 2
        NSColor.colorWithCalibratedRed_green_blue_alpha_(
            0.95, 0.15, 0.15, self._alpha
        ).set()
        dot = NSBezierPath.bezierPath()
        dot.appendBezierPathWithOvalInRect_(
            NSMakeRect(cx - _DOT_R, cy - _DOT_R, _DOT_R * 2, _DOT_R * 2)
        )
        dot.fill()

        # "Recording…" label
        para = NSMutableParagraphStyle.alloc().init()
        para.setAlignment_(NSCenterTextAlignment)
        attrs = {
            NSFontAttributeName: NSFont.systemFontOfSize_(14),
            NSForegroundColorAttributeName: NSColor.whiteColor(),
            NSParagraphStyleAttributeName: para,
        }
        label_rect = NSMakeRect(36, (_PANEL_H - 18) / 2, _PANEL_W - 48, 18)
        NSAttributedString.alloc().initWithString_attributes_(
            "Recording…", attrs
        ).drawInRect_(label_rect)

    def tick_(self, _timer):
        self._alpha = 0.25 if self._alpha > 0.5 else 1.0
        self.setNeedsDisplay_(True)


class RecordingOverlay:
    def __init__(self):
        self._timer = None
        screen = NSScreen.mainScreen()
        sw = screen.frame().size.width
        sh = screen.frame().size.height
        x = (sw - _PANEL_W) / 2
        y = sh - _PANEL_H - 24

        panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(x, y, _PANEL_W, _PANEL_H),
            NSNonactivatingPanelMask | NSBorderlessWindowMask,
            2,
            False,
        )
        panel.setLevel_(101)  # NSPopUpMenuWindowLevel
        panel.setOpaque_(False)
        panel.setBackgroundColor_(NSColor.clearColor())
        panel.setHasShadow_(True)
        panel.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces
            | NSWindowCollectionBehaviorStationary
            | NSWindowCollectionBehaviorIgnoresCycle
        )
        panel.setIgnoresMouseEvents_(True)
        panel.setAlphaValue_(0.0)

        view = _RecordingView.alloc().initWithFrame_(
            NSMakeRect(0, 0, _PANEL_W, _PANEL_H)
        )
        view._setup()
        panel.setContentView_(view)

        self._panel = panel
        self._view = view

    def show(self):
        self._panel.setAlphaValue_(1.0)
        self._panel.orderFrontRegardless()
        self._timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.55, self._view, "tick:", None, True
        )

    def hide(self):
        if self._timer is not None:
            self._timer.invalidate()
            self._timer = None
        self._panel.setAlphaValue_(0.0)
        self._panel.orderOut_(None)
