import { describe, expect, it } from 'vitest'

import { bearingDeg, estimateMotion, formatDms, haversineM, MPS_TO_KNOTS } from './geo'

const origin = { lat: 22.6166, lon: 120.279 }

describe('haversineM', () => {
  it('one degree of latitude is about 111.2 km', () => {
    expect(haversineM({ lat: 0, lon: 0 }, { lat: 1, lon: 0 })).toBeCloseTo(111_195, -1)
  })

  it('is zero for the same point', () => {
    expect(haversineM(origin, origin)).toBe(0)
  })
})

describe('bearingDeg', () => {
  it.each([
    [{ lat: 22.62, lon: 120.279 }, 0],
    [{ lat: 22.6166, lon: 120.28 }, 90],
    [{ lat: 22.61, lon: 120.279 }, 180],
    [{ lat: 22.6166, lon: 120.27 }, 270],
  ])('points toward %o at %i°', (target, expected) => {
    expect(bearingDeg(origin, target)).toBeCloseTo(expected, 1)
  })
})

describe('estimateMotion', () => {
  // 每 200 ms 向北移動 2 m → 10 m/s
  const track = Array.from({ length: 10 }, (_, i) => ({
    lat: origin.lat + (2 * i) / 111_195,
    lon: origin.lon,
    t: 1_000 + i * 200,
  }))

  it('estimates speed in knots and course from the last segments', () => {
    const motion = estimateMotion(track)!
    expect(motion.speedKnots).toBeCloseTo(10 * MPS_TO_KNOTS, 1)
    expect(motion.courseDeg).toBeCloseTo(0, 1)
  })

  it('returns null without enough data', () => {
    expect(estimateMotion(track.slice(0, 1))).toBeNull()
    expect(estimateMotion([track[0]!, { ...track[1]!, t: track[0]!.t }])).toBeNull()
  })

  it('has no course when stationary', () => {
    const still = [
      { ...origin, t: 0 },
      { ...origin, t: 1000 },
    ]
    expect(estimateMotion(still)).toEqual({ speedKnots: 0, courseDeg: null })
  })
})

describe('formatDms', () => {
  it('formats latitude and longitude with hemisphere', () => {
    expect(formatDms(22.6166, 'lat')).toBe(`22°36'59.8"N`)
    expect(formatDms(-120.279, 'lon')).toBe(`120°16'44.4"W`)
  })

  it('carries rounding into minutes instead of printing 60.0 seconds', () => {
    expect(formatDms(22.999999, 'lat')).toBe(`23°00'00.0"N`)
  })
})
