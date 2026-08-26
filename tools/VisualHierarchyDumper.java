package com.android.commands.uiautomator;

import android.app.UiAutomation;
import android.graphics.Rect;
import android.util.Xml;
import android.view.accessibility.AccessibilityNodeInfo;
import java.io.FileOutputStream;
import org.xmlpull.v1.XmlSerializer;

public final class VisualHierarchyDumper {
    private static String safe(CharSequence value) {
        if (value == null) {
            return "";
        }
        String raw = value.toString();
        StringBuilder out = new StringBuilder(raw.length());
        for (int i = 0; i < raw.length(); i++) {
            char c = raw.charAt(i);
            if (c == '\t' || c == '\n' || c == '\r' || c >= 0x20) {
                out.append(c);
            }
        }
        return out.toString();
    }

    private static void attr(XmlSerializer xml, String name, Object value) throws Exception {
        xml.attribute("", name, String.valueOf(value));
    }

    private static void node(XmlSerializer xml, AccessibilityNodeInfo info, int index) throws Exception {
        xml.startTag("", "node");
        attr(xml, "index", index);
        attr(xml, "text", safe(info.getText()));
        attr(xml, "resource-id", safe(info.getViewIdResourceName()));
        attr(xml, "class", safe(info.getClassName()));
        attr(xml, "package", safe(info.getPackageName()));
        attr(xml, "content-desc", safe(info.getContentDescription()));
        attr(xml, "checkable", info.isCheckable());
        attr(xml, "checked", info.isChecked());
        attr(xml, "clickable", info.isClickable());
        attr(xml, "enabled", info.isEnabled());
        attr(xml, "focusable", info.isFocusable());
        attr(xml, "focused", info.isFocused());
        attr(xml, "scrollable", info.isScrollable());
        attr(xml, "long-clickable", info.isLongClickable());
        attr(xml, "password", info.isPassword());
        attr(xml, "selected", info.isSelected());
        Rect bounds = new Rect();
        info.getBoundsInScreen(bounds);
        attr(xml, "bounds", "[" + bounds.left + "," + bounds.top + "][" + bounds.right + "," + bounds.bottom + "]");
        for (int i = 0; i < info.getChildCount(); i++) {
            AccessibilityNodeInfo child = info.getChild(i);
            if (child != null) {
                try {
                    node(xml, child, i);
                } finally {
                    child.recycle();
                }
            }
        }
        xml.endTag("", "node");
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 1) {
            throw new IllegalArgumentException("output path required");
        }
        UiAutomationShellWrapper wrapper = new UiAutomationShellWrapper();
        wrapper.connect();
        try {
            wrapper.setCompressedLayoutHierarchy(true);
            UiAutomation automation = wrapper.getUiAutomation();
            AccessibilityNodeInfo root = automation.getRootInActiveWindow();
            if (root == null) {
                throw new IllegalStateException("null accessibility root");
            }
            try {
                FileOutputStream stream = new FileOutputStream(args[0]);
                try {
                    XmlSerializer xml = Xml.newSerializer();
                    xml.setOutput(stream, "UTF-8");
                    xml.startDocument("UTF-8", true);
                    xml.startTag("", "hierarchy");
                    attr(xml, "rotation", 0);
                    node(xml, root, 0);
                    xml.endTag("", "hierarchy");
                    xml.endDocument();
                    xml.flush();
                } finally {
                    stream.close();
                }
            } finally {
                root.recycle();
            }
        } finally {
            wrapper.disconnect();
        }
    }

    private VisualHierarchyDumper() {}
}
