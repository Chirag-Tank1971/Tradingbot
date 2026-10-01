import { NextResponse } from "next/server";
import { forwardGetToBackend } from "../../_lib/backend";

export async function GET() {
  const result = await forwardGetToBackend("/api/bot/status");
  return NextResponse.json(result);
}
