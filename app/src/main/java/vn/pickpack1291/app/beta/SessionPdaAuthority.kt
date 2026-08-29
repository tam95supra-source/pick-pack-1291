package vn.pickpack1291.app.beta

/** Pure regression seam for PDA-EXIT-001. Scalar legacy PDA fields are intentionally absent. */
internal object SessionPdaAuthority {
    data class Decision(val authoritative:Boolean,val activePdaId:String?){
        val needsSnapshot:Boolean get()=!authoritative
        val requiresCheck:Boolean get()=authoritative&&!activePdaId.isNullOrBlank()
    }

    fun decide(authoritativeAssignmentsPresent:Boolean,activePdaIds:List<String>):Decision{
        if(!authoritativeAssignmentsPresent)return Decision(false,null)
        return Decision(true,activePdaIds.firstOrNull{it.isNotBlank()}?.trim())
    }
}
