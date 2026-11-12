export function materialRole(name: string | null | undefined): 'terrain' | 'water' {
  return name === 'painted-water' || name === 'painted-water-flatShaded' ? 'water' : 'terrain';
}
