import { describe, expect, it } from "vitest";

import { applySuggestionToText, countWords, parseUserCsv } from "./school-data";

describe("parseUserCsv", () => {
  it("parses student import rows", () => {
    const result = parseUserCsv(
      "email,display_name,student_number,level,class_name\ns1@example.edu,Student One,S0002,P5,P5A",
    );

    expect(result.errors).toEqual([]);
    expect(result.rows).toEqual([
      {
        external_user_id: undefined,
        email: "s1@example.edu",
        display_name: "Student One",
        student_number: "S0002",
        level: "P5",
        class_name: "P5A",
        staff_code: undefined,
      },
    ]);
  });

  it("rejects missing required headers", () => {
    const result = parseUserCsv("email,class_name\ns1@example.edu,P5A");

    expect(result.rows).toEqual([]);
    expect(result.errors[0]).toContain("Missing required headers");
  });

  it("rejects rows without an email or display name", () => {
    const result = parseUserCsv("email,display_name\ns1@example.edu,");

    expect(result.rows).toEqual([]);
    expect(result.errors[0]).toContain("requires email and display_name");
  });

  it("parses quoted CSV fields with commas and escaped quotes", () => {
    const result = parseUserCsv(
      'email,display_name,student_number,level,class_name\ns2@example.edu,"Chan, ""Ada""",S0003,P5,P5A',
    );

    expect(result.errors).toEqual([]);
    expect(result.rows[0].display_name).toBe('Chan, "Ada"');
  });

  it("rejects malformed rows with too many columns", () => {
    const result = parseUserCsv("email,display_name\ns1@example.edu,Student One,Unexpected");

    expect(result.rows).toEqual([]);
    expect(result.errors[0]).toContain("columns but header has");
  });
});

describe("countWords", () => {
  it("counts words across whitespace", () => {
    expect(countWords(" One  short\nstory ")).toBe(3);
  });

  it("returns zero for blank text", () => {
    expect(countWords("   ")).toBe(0);
  });
});

describe("applySuggestionToText", () => {
  it("replaces only the suggestion span", () => {
    expect(
      applySuggestionToText(
        "i dont like teh error",
        {
          id: "suggestion-1",
          rule_id: "MORFOLOGIK_RULE_EN_US",
          category: "TYPOS",
          message: "Possible spelling mistake.",
          short_message: "Spelling",
          offset: 12,
          length: 3,
          replacements: ["the"],
          severity: "WARNING",
          level: "WORD",
        },
        "the",
      ),
    ).toBe("i dont like the error");
  });
});
