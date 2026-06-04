export interface Source {
  n: number;
  title: string;
  ref: string;
  url: string;
  source_type: string;
}

export type ChatEvent =
  | { type: "token"; text: string }
  | { type: "done"; answer: string; sources: Source[] };

export interface Message {
  role: "user" | "assistant";
  text: string;
  sources?: Source[];
  streaming?: boolean;
}
