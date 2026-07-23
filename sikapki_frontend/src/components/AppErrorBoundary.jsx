import { Component } from 'react'

export default class AppErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(error, info) {
    console.error('SIKAP-KI frontend error:', error, info)
  }

  render() {
    if (this.state.hasError) {
      return (
        <main className="flex min-h-screen items-center justify-center bg-gov-paper px-4 text-gov-navy">
          <section className="w-full max-w-lg rounded-2xl border border-red-200 bg-white p-6 text-center shadow-soft">
            <p className="text-xl font-black">Halaman mengalami kendala</p>
            <p className="mt-3 text-sm leading-6 text-slate-600">Tampilan tidak dapat dilanjutkan, tetapi data aplikasi tetap aman. Muat ulang halaman untuk mencoba kembali.</p>
            <button type="button" onClick={() => window.location.reload()} className="mt-5 min-h-11 rounded-lg bg-gov-teal px-5 text-sm font-bold text-white hover:bg-teal-700">
              Muat ulang halaman
            </button>
          </section>
        </main>
      )
    }
    return this.props.children
  }
}
