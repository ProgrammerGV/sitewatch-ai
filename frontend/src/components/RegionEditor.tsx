import { useRef, useState } from 'react'
import type { PointerEvent } from 'react'
import { Crosshair } from 'lucide-react'
import type { Region } from '../types'
export function RegionEditor({
  roi,
  change,
  hasFrame,
}: {
  roi: Region
  change: (r: Region) => void
  hasFrame: boolean
}) {
  const element = useRef<HTMLDivElement>(null)
  const anchor = useRef<[number, number] | null>(null)
  const [ratio, setRatio] = useState(4 / 3)
  const point = (event: PointerEvent) => {
    const rect = element.current!.getBoundingClientRect()
    return [
      Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width)),
      Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height)),
    ] as [number, number]
  }
  return (
    <div
      className="region-editor"
      ref={element}
      style={{ aspectRatio: ratio }}
      onPointerDown={(e) => {
        if (!hasFrame) return
        anchor.current = point(e)
        e.currentTarget.setPointerCapture(e.pointerId)
      }}
      onPointerMove={(e) => {
        if (!anchor.current) return
        const [x, y] = point(e)
        const [ax, ay] = anchor.current
        change([Math.min(ax, x), Math.min(ay, y), Math.abs(ax - x), Math.abs(ay - y)])
      }}
      onPointerUp={(e) => {
        if (!anchor.current) return
        const [x, y] = point(e)
        const [ax, ay] = anchor.current
        if (Math.abs(ax - x) < 0.01 || Math.abs(ay - y) < 0.01) change([0, 0, 1, 1])
        anchor.current = null
      }}
      onPointerCancel={() => {
        anchor.current = null
      }}
    >
      {hasFrame ? (
        <img
          src="/api/monitor/stream"
          alt="Last captured scene for region selection"
          draggable={false}
          onLoad={(e) => setRatio(e.currentTarget.naturalWidth / e.currentTarget.naturalHeight)}
        />
      ) : (
        <div className="region-hint">
          <Crosshair size={32} />
          <p>Run monitoring once to capture your scene.</p>
          <small>You can still use the full image as your region.</small>
        </div>
      )}
      <svg
        viewBox="0 0 1000 1000"
        preserveAspectRatio="none"
        aria-label="Selected monitoring region"
      >
        <rect x={roi[0] * 1000} y={roi[1] * 1000} width={roi[2] * 1000} height={roi[3] * 1000} />
      </svg>
    </div>
  )
}
