package vn.pickpack1291.app.beta

/**
 * Canonical payload for a PDA-only change/return.
 * Unrelated session resources are intentionally omitted so Service preserves
 * its authoritative USER_PICK / PACK_TABLE / USER_PACK / shift / work choice.
 */
object PdaOnlyMutationPayload {
    private val unrelated = setOf("shift","work_choice","user_pick","pack_table","user_pack","resource_note")

    fun fields(
        sessionId:String,
        mnv:String,
        pdaSerial:String,
        kind:String,
        reason:String,
        idempotencyKey:String,
    ):Map<String,String> {
        require(sessionId.isNotBlank()) { "SESSION_ID_REQUIRED" }
        require(mnv.isNotBlank()) { "MNV_REQUIRED" }
        require(idempotencyKey.isNotBlank()) { "IDEMPOTENCY_KEY_REQUIRED" }
        val out=linkedMapOf(
            "session_id" to sessionId.trim(),
            "mnv" to mnv.trim(),
            "pda_serial" to pdaSerial.trim(),
            "mutation_kind" to "EDIT",
            "audit_note" to "${kind.trim()} PDA • ${reason.trim()}",
            "idempotency_key" to idempotencyKey.trim(),
        )
        check(out.keys.none { it in unrelated }) { "PDA_ONLY_PAYLOAD_CONTAINS_UNRELATED_RESOURCE" }
        return out
    }
}
