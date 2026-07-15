export const airbnbColors = {
  rausch: '#FF5A5F',
  babu: '#00A699',
  hackberry: '#484848',
  foggy: '#767676',
  border: '#EBEBEB',
  background: '#FFFFFF',
  pageGray: '#F7F7F7',
} as const;

export type AppStatus =
  | 'Live'
  | 'In Development'
  | 'In Progress'
  | 'Beta'
  | 'Planned'
  | 'POC'
  | 'Maintenance'
  | 'Deprecated';
