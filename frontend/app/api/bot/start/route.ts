import { NextRequest, NextResponse } from "next/server";
import { forwardToBackend } from "../../_lib/backend";

export async function POST(request: NextRequest) {
  try {
    const payload = await request.json();
    const result = await forwardToBackend("/api/bot/start", payload);
    return NextResponse.json(result);
  } catch (error) {
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "Invalid request",
      },
      { status: 400 },
    );
  }
}
