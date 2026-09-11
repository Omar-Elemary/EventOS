import { Component, type ReactNode } from "react";

type Props = { children: ReactNode };
type State = { message: string | null };

export class ErrorBoundary extends Component<Props, State> {
  state: State = { message: null };

  static getDerivedStateFromError(error: Error): State {
    return { message: error.message || String(error) };
  }

  render() {
    if (this.state.message) {
      return (
        <div className="mx-auto max-w-xl p-8">
          <p className="font-display text-2xl font-extrabold uppercase">The UI crashed</p>
          <p className="mt-3 font-mono text-sm font-bold">{this.state.message}</p>
          <button
            className="mt-6 rounded-lg border-2 border-black bg-nb-yellow px-4 py-2 font-display text-xs font-extrabold uppercase shadow-nb"
            onClick={() => window.location.reload()}
          >
            Reload
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
