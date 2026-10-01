import { NextRequest, NextResponse } from "next/server";
import { forwardGetToBackend } from "../_lib/backend";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const symbol = searchParams.get("symbol") || "BTCUSDT";
  const interval = searchParams.get("interval") || "1h";
  const limit = searchParams.get("limit") || "500";

  const result = await forwardGetToBackend<{ candles: unknown[] }>("/api/klines", {
    symbol,
    interval,
    limit,
  });

  return NextResponse.json(result);
}
