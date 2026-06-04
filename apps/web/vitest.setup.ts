import "@testing-library/jest-dom/vitest";

// jsdom does not implement layout methods; stub for components that auto-scroll.
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => {};
}
