package vn.pickpack1291.app.beta

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PdaOnlyMutationPayloadTest {
    @Test fun changePdaDoesNotReplayUnrelatedResources() {
        val fields=PdaOnlyMutationPayload.fields("session-1","30001","MT90-NEW","Đổi","Hỏng nút","idem-1")
        assertEquals("MT90-NEW",fields["pda_serial"])
        assertEquals("session-1",fields["session_id"])
        for(key in listOf("shift","work_choice","user_pick","pack_table","user_pack","resource_note")) {
            assertFalse("must omit $key",fields.containsKey(key))
        }
        assertTrue(fields["audit_note"].orEmpty().contains("Đổi PDA"))
    }

    @Test fun returnPdaAllowsEmptySerialWithoutTouchingOtherResources() {
        val fields=PdaOnlyMutationPayload.fields("session-2","30002","","Trả","Cuối ca","idem-2")
        assertEquals("",fields["pda_serial"])
        assertEquals("EDIT",fields["mutation_kind"])
        assertEquals(6,fields.size)
    }
}
