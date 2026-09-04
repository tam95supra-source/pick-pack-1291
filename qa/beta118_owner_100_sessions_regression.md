# Beta118 OWNER 100 sessions review regression

- Exact receipt contains 100 unique MNV and 100 unique session IDs.
- Live canonical readback must contain the exact receipt set, ACTIVE and in-only.
- Reconciliation shift matching is canonical and case-insensitive for Ca 1 / Ca HC / Ca 2.
- Legacy synthetic rows with CA 1 / CA HC / CA 2 remain visible without destructive reseed.
- Exact-set verification must compare canonical, review projection, local cache and UI; total counts alone are insufficient.
- Stable data, main, signer and authority remain untouched.
