import math
import objc
from AppKit import (
    NSPanel, NSView, NSColor, NSBezierPath, NSScreen, NSTimer,
    NSMakeRect, NSNonactivatingPanelMask, NSBorderlessWindowMask,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorStationary,
    NSWindowCollectionBehaviorIgnoresCycle,
)

_PANEL_W = 240
_PANEL_H = 56
_CORNER = 28
_DOT_R = 6

_NUM_BARS = 14
_BAR_W = 5
_BAR_GAP = 6
_BAR_MAX_H = 30
_BAR_MIN_H = 5

# Pre-computed phase offsets so each bar oscillates independently
_PHASES = [i * (2 * math.pi / _NUM_BARS) for i in range(_NUM_BARS)]

# Center dot + waveform together inside the pill
_WAVE_W = _NUM_BARS * _BAR_W + (_NUM_BARS - 1) * _BAR_GAP
_DOT_GAP = 10                                          # gap between dot and first bar
_CONTENT_W = _DOT_R * 2 + _DOT_GAP + _WAVE_W          # total content width
_LEFT = (_PANEL_W - _CONTENT_W) / 2                   # left margin to center it
_DOT_CX = _LEFT + _DOT_R                               # dot center x
_WAVE_X = _LEFT + _DOT_R * 2 + _DOT_GAP               # waveform start x


class _RecordingView(NSView):

    @objc.python_method
    def _setup(self):
        self._t = 0.0

    def drawRect_(self, rect):
        # Dark pill
        NSColor.colorWithCalibratedRed_green_blue_alpha_(0.08, 0.08, 0.08, 0.96).set()
        pill = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
            NSMakeRect(0, 0, _PANEL_W, _PANEL_H), _CORNER, _CORNER
        )
        pill.fill()

        # Subtle border
        NSColor.colorWithCalibratedWhite_alpha_(1.0, 0.18).set()
        border = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
            NSMakeRect(0.75, 0.75, _PANEL_W - 1.5, _PANEL_H - 1.5), _CORNER, _CORNER
        )
        border.setLineWidth_(1.5)
        border.stroke()

        # Red dot
        cy = _PANEL_H / 2
        NSColor.colorWithCalibratedRed_green_blue_alpha_(0.95, 0.18, 0.18, 1.0).set()
        dot = NSBezierPath.bezierPath()
        dot.appendBezierPathWithOvalInRect_(
            NSMakeRect(_DOT_CX - _DOT_R, cy - _DOT_R, _DOT_R * 2, _DOT_R * 2)
        )
        dot.fill()

        # Waveform bars
        NSColor.colorWithCalibratedWhite_alpha_(1.0, 0.92).set()
        t = self._t
        for i in range(_NUM_BARS):
            # Each bar oscillates at slightly different speed + phase
            wave = 0.5 + 0.5 * math.sin(t * 4.5 + _PHASES[i])
            h = _BAR_MIN_H + (_BAR_MAX_H - _BAR_MIN_H) * wave
            x = _WAVE_X + i * (_BAR_W + _BAR_GAP)
            y = (cy) - h / 2
            r = _BAR_W / 2
            bar = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                NSMakeRect(x, y, _BAR_W, h), r, r
            )
            bar.fill()

    def tick_(self, _timer):
        self._t += 0.07
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
        panel.setLevel_(101)
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
            0.05, self._view, "tick:", None, True
        )

    def hide(self):
        if self._timer is not None:
            self._timer.invalidate()
            self._timer = None
        self._panel.setAlphaValue_(0.0)
        self._panel.orderOut_(None)
