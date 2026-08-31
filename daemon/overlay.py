import objc
from AppKit import (
    NSPanel, NSView, NSColor, NSBezierPath, NSScreen,
    NSMakeRect, NSFont, NSString, NSFontAttributeName,
    NSForegroundColorAttributeName, NSMutableParagraphStyle,
    NSParagraphStyleAttributeName, NSCenterTextAlignment,
    NSNonactivatingPanelMask, NSBorderlessWindowMask,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorStationary,
    NSWindowCollectionBehaviorIgnoresCycle,
)
from Quartz import (
    CALayer, CABasicAnimation, kCAMediaTimingFunctionEaseInEaseOut,
    kCAFillModeForwards,
)

_PANEL_W = 200
_PANEL_H = 64
_DOT_SIZE = 14
_CORNER = 16


class _RecordingView(NSView):

    @objc.python_method
    def _setup(self):
        self.setWantsLayer_(True)
        bg = self.layer()
        bg.setBackgroundColor_(NSColor.colorWithWhite_alpha_(0.12, 0.88).CGColor())
        bg.setCornerRadius_(_CORNER)

        # Pulsing red dot (CALayer)
        dot = CALayer.layer()
        dot.setFrame_(((16, (_PANEL_H - _DOT_SIZE) / 2), (_DOT_SIZE, _DOT_SIZE)))
        dot.setBackgroundColor_(NSColor.systemRedColor().CGColor())
        dot.setCornerRadius_(_DOT_SIZE / 2)

        pulse = CABasicAnimation.animationWithKeyPath_("opacity")
        pulse.setFromValue_(1.0)
        pulse.setToValue_(0.25)
        pulse.setDuration_(0.75)
        pulse.setAutoreverses_(True)
        pulse.setRepeatCount_(1e9)
        pulse.setTimingFunction_(
            objc.lookUpClass("CAMediaTimingFunction")
            .functionWithName_(kCAMediaTimingFunctionEaseInEaseOut)
        )
        dot.addAnimation_forKey_(pulse, "pulse")

        self.layer().addSublayer_(dot)
        self._dot = dot

        # "Recording…" label drawn in drawRect_
        self._label = "Recording…"

    def drawRect_(self, rect):
        para = NSMutableParagraphStyle.alloc().init()
        para.setAlignment_(NSCenterTextAlignment)
        attrs = {
            NSFontAttributeName: NSFont.systemFontOfSize_weight_(14, 0.0),
            NSForegroundColorAttributeName: NSColor.whiteColor(),
            NSParagraphStyleAttributeName: para,
        }
        label_rect = NSMakeRect(36, (_PANEL_H - 20) / 2, _PANEL_W - 44, 20)
        NSString.stringWithString_(self._label).drawInRect_withAttributes_(
            label_rect, attrs
        )


class RecordingOverlay:
    def __init__(self):
        screen = NSScreen.mainScreen()
        sw = screen.frame().size.width
        x = (sw - _PANEL_W) / 2
        y = screen.frame().size.height - _PANEL_H - 20  # 20pt from top

        panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(x, y, _PANEL_W, _PANEL_H),
            NSNonactivatingPanelMask | NSBorderlessWindowMask,
            2,  # NSBackingStoreBuffered
            False,
        )
        panel.setLevel_(25)  # NSFloatingWindowLevel+1, above most HUDs
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

    def show(self):
        self._panel.setAlphaValue_(1.0)
        self._panel.orderFrontRegardless()

    def hide(self):
        self._panel.setAlphaValue_(0.0)
        self._panel.orderOut_(None)
