import test from "node:test";import assert from "node:assert/strict";import fs from "node:fs";
test("DR uses canonical service core instead of duplicated business rules",()=>{const h=fs.readFileSync(new URL("../src/handler.ts",import.meta.url),"utf8");assert.match(h,/service\/src\/core/);assert.match(h,/service\/src\/legacy/);assert.doesNotMatch(h,/SUPABASE/i)});
test("writer is fenced unless ACTIVE_WRITE",()=>{const h=fs.readFileSync(new URL("../src/handler.ts",import.meta.url),"utf8");assert.match(h,/DR_WRITER_MODE!==\"ACTIVE_WRITE\"/);assert.match(h,/DR_PASSIVE_FENCED/)});
