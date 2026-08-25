import test from "node:test";
import assert from "node:assert/strict";
import { fetchAllRankingPages } from "./api.js";

test("ranking loader combines every API page and preserves snapshot id", async () => {
  const calls=[];
  const request=async (path)=>{
    calls.push(path);
    const page=Number(new URL(`http://local${path}`).searchParams.get("page"));
    return {items:Array.from({length:page===3?50:200},(_,index)=>({symbol:`${page}-${index}`})),
            pagination:{page,pages:3,total:450,page_size:200}};
  };
  const result=await fetchAllRankingPages("snapshot / final",request);
  assert.equal(result.items.length,450);
  assert.equal(calls.length,3);
  assert.ok(calls.every((path)=>path.includes("snapshot_id=snapshot%20%2F%20final")));
});

test("ranking loader does not issue extra requests for one page", async () => {
  let calls=0;
  const result=await fetchAllRankingPages(null,async ()=>{calls++;return {items:[{symbol:"2330"}],pagination:{pages:1,total:1}}});
  assert.equal(calls,1);
  assert.equal(result.items[0].symbol,"2330");
});

test("ranking loader rejects an unreasonable pagination response", async () => {
  await assert.rejects(
    fetchAllRankingPages(null, async () => ({ items: [], pagination: { pages: 1001 } })),
    /分頁數異常/,
  );
});
