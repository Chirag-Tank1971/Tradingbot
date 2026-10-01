import { NextResponse } from "next/server";
import { forwardToBackend } from "../../_lib/backend";

export async function POST() {
  const result = await forwardToBackend("/api/bot/reset", {});
  return NextResponse.json(result);
}
