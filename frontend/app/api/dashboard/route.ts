import { NextRequest, NextResponse } from "next/server";

import { forwardToBackend } from "../_lib/backend";

type DashboardPayload = {
  symbol?: string;
};

type DashboardResponse = {
  dashboard?: {
    symbol: string;
    summary: Record<string, string>;
    balances: Record<string, string>[];
    positions: Record<string, string>[];
    open_orders: Record<string, string>[];
    recent_orders: Record<string, string>[];
  };
};

export async function POST(request: NextRequest) {
  let payload: DashboardPayload;

  try {
    payload = await request.json();
  } catch {
    payload = {};
  }

  const backendResult = await forwardToBackend<DashboardResponse>(
    "/api/dashboard",
    payload,
  );
  const status = backendResult.success ? 200 : 400;

  return NextResponse.json(backendResult, { status });
}

