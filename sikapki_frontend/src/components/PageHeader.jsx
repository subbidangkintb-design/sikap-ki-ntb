export default function PageHeader({ eyebrow, title, description }) {
  return (
    <section className="border-b border-gov-line bg-white">
      <div className="mx-auto max-w-6xl px-4 py-6 sm:py-8">
        {eyebrow ? <p className="mb-2 text-sm font-bold uppercase tracking-wide text-gov-teal">{eyebrow}</p> : null}
        <h1 className="max-w-3xl text-2xl font-bold leading-tight text-gov-navy sm:text-3xl md:text-4xl">{title}</h1>
        {description ? <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-700 sm:text-base sm:leading-7">{description}</p> : null}
      </div>
    </section>
  )
}
