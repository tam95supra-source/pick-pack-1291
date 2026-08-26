package vn.pickpack1291.visual;

import com.android.uiautomator.core.Configurator;
import com.android.uiautomator.testrunner.UiAutomatorTestCase;

public final class VisualHierarchyDumper extends UiAutomatorTestCase {
    public void testDump() throws Exception {
        Configurator.getInstance().setWaitForIdleTimeout(0);
        getUiDevice().setCompressedLayoutHeirarchy(true);
        getUiDevice().dumpWindowHierarchy("beta77-window.xml");
    }
}
