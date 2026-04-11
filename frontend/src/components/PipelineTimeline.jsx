const STATUS_STYLES = {
  agendado: { bg: 'bg-blue-100', text: 'text-blue-700', label: 'Agendado' },
  processando: { bg: 'bg-yellow-100', text: 'text-yellow-700', label: 'Processando' },
  concluido: { bg: 'bg-green-100', text: 'text-green-700', label: 'Concluído' },
  erro: { bg: 'bg-red-100', text: 'text-red-700', label: 'Erro' },
  ativo: { bg: 'bg-blue-100', text: 'text-blue-700', label: 'Agendado' },
}

function formatHour(h) {
  return `${String(h).padStart(2, '0')}:00`
}

export default function PipelineTimeline({ schedule }) {
  if (!schedule || schedule.length === 0) {
    return (
      <div className="text-center py-8 text-gray-400">
        Nenhum app agendado para hoje.
      </div>
    )
  }

  const sorted = [...schedule].sort((a, b) => a.hora - b.hora)
  const currentHour = new Date().getHours()

  return (
    <div className="space-y-3">
      {sorted.map((item, idx) => {
        const style = STATUS_STYLES[item.status] || STATUS_STYLES.agendado
        const isPast = item.hora < currentHour
        const isCurrent = item.hora === currentHour

        return (
          <div
            key={idx}
            className={`flex items-center gap-4 p-3 rounded-lg border transition-colors ${
              isCurrent
                ? 'border-indigo-300 bg-indigo-50'
                : isPast
                  ? 'border-gray-200 bg-gray-50'
                  : 'border-gray-200 bg-white'
            }`}
          >
            {/* Timeline dot */}
            <div className="flex flex-col items-center">
              <div
                className={`w-3 h-3 rounded-full ${
                  isCurrent ? 'bg-indigo-500 ring-4 ring-indigo-100' : isPast ? 'bg-gray-400' : 'bg-gray-300'
                }`}
              />
            </div>

            {/* Hour */}
            <span className={`text-sm font-mono font-medium w-12 ${isCurrent ? 'text-indigo-600' : 'text-gray-500'}`}>
              {formatHour(item.hora)}
            </span>

            {/* App name */}
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">{item.app}</p>
              {item.categoria && (
                <p className="text-xs text-gray-500">{item.categoria}</p>
              )}
            </div>

            {/* Status badge */}
            <span className={`px-2.5 py-1 text-xs font-medium rounded-full ${style.bg} ${style.text}`}>
              {style.label}
            </span>
          </div>
        )
      })}
    </div>
  )
}
