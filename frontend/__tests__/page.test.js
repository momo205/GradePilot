import { render, screen } from "@testing-library/react";
import Home from "../src/app/page";

describe("GradePilot frontend", () => {

  test("renders the GradePilot title", () => {
    render(<Home />);
    const elements = screen.getAllByText(/gradepilot/i);
    expect(elements.length).toBeGreaterThan(0);
    expect(elements[0]).toBeInTheDocument();
  });

  test("renders the features section", () => {
    render(<Home />);
    expect(screen.getByText(/everything you need to run your week/i)).toBeInTheDocument();
    expect(screen.getByText(/syllabus parsing/i)).toBeInTheDocument();
  });

  test("renders the how it works section", () => {
    render(<Home />);
    expect(screen.getAllByText(/how it works/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/upload your syllabus or notes/i)).toBeInTheDocument();
  });

  test("renders the get started CTA", () => {
    render(<Home />);
    expect(screen.getAllByText(/get started/i).length).toBeGreaterThan(0);
  });

});
