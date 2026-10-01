import { NextRequest, NextResponse } from "next/server";

import { forwardToBackend } from "../_lib/backend";

type OrderPayload = {
  symbol?: string;
  side?: string;
  type?: string;
  quantity?: string;
  price?: string;
};

type OrderResponse = {
  order?: {
    order_id: string;
    status: string;
    executed_qty: string;
    average_price: string;
    client_order_id: string;
  };
};

export async function POST(request: NextRequest) {
  let payload: OrderPayload;

  try {
    payload = await request.json();
  } catch {
    return NextResponse.json(
      { success: false, error: "Request body must be valid JSON." },
      { status: 400 },
    );
  }

  const backendResult = await forwardToBackend<OrderResponse>("/api/orders", payload);
  const status = backendResult.success ? 200 : 400;

  return NextResponse.json(backendResult, { status });
}

