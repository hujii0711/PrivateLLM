/** POST+SSE 응답을 청크 단위로 받아 완성된 data 페이로드(JSON 문자열)를 반환하는 파서. */
export class SSEParser {
  private buf = "";

  push(chunk: string): string[] {
    this.buf += chunk.replace(/\r\n/g, "\n");
    const out: string[] = [];
    let idx: number;
    while ((idx = this.buf.indexOf("\n\n")) !== -1) {
      const frame = this.buf.slice(0, idx);
      this.buf = this.buf.slice(idx + 2);
      const data = frame
        .split("\n")
        .filter((l) => l.startsWith("data:"))
        .map((l) => l.slice(5).replace(/^ /, ""))
        .join("\n");
      if (data) out.push(data);
    }
    return out;
  }
}
