import { AlertCircle, CheckCircle2, Info } from 'lucide-react'

const toneMap = {
  info: 'border-gov-line bg-white text-gov-navy',
  success: 'border-emerald-200 bg-emerald-50 text-emerald-950',
  warning: 'border-amber-200 bg-amber-50 text-amber-950',
  error: 'border-red-200 bg-red-50 text-red-950',
}

const iconMap = {
  info: Info,
  success: CheckCircle2,
  warning: AlertCircle,
  error: AlertCircle,
}

export default function StatusNotice({ tone = 'info', title, children }) {
  const Icon = iconMap[tone] || Info
  return (
    <div className={`rounded-lg border p-4 ${toneMap[tone] || toneMap.info}`}>
      <div className="flex gap-3">
        <Icon className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
        <div>
          {title ? <p className="font-bold">{title}</p> : null}
          <div className="mt-1 text-sm leading-6">{children}</div>
        </div>
      </div>
    </div>
  )
}
