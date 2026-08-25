package vn.pickpack1291.app.beta

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class DropReceiveQrParserTest {
    @Test fun authoritativeSampleParsesDoAndPackageCount(){
        val p=DropReceiveQrParser.parse("2AD7|7081639744|SOWIN8H9KA2BL3C|PB1260823D8CB48|CX1.1.1|5/13")
        assertEquals("7081639744",p?.doNumber)
        assertEquals(13,p?.packageCount)
    }
    @Test fun missingSecondPartDoesNotInventDo(){
        assertNull(DropReceiveQrParser.parse("2AD7||SOWIN8H9KA2BL3C|PB1260823D8CB48|CX1.1.1|5/13"))
    }
    @Test fun tailWithoutSlashFallsBackToManual(){
        assertNull(DropReceiveQrParser.parse("2AD7|7081639744|SOWIN8H9KA2BL3C|PB1260823D8CB48|CX1.1.1|13"))
    }
    @Test fun tailWithoutNumberAfterSlashFallsBackToManual(){
        assertNull(DropReceiveQrParser.parse("2AD7|7081639744|SOWIN8H9KA2BL3C|PB1260823D8CB48|CX1.1.1|5/"))
    }
}
