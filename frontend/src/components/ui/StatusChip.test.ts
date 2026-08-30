import { describe, expect, it } from "vitest";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { StatusChip } from "./StatusChip";

describe("StatusChip glass labels", () => {
  it("maps coverage and policy enums to human words", () => {
    expect(renderToStaticMarkup(createElement(StatusChip, { status: "named_gap" }))).toContain("Coverage gap");
    expect(renderToStaticMarkup(createElement(StatusChip, { status: "mule_credit_restrict" }))).toContain(
      "Restrict (payee credit)",
    );
    expect(renderToStaticMarkup(createElement(StatusChip, { status: "live_rule" }))).toContain("Live rule");
    expect(renderToStaticMarkup(createElement(StatusChip, { status: "draft_rule" }))).toContain("Draft rule");
  });
});
