const mockData = [
  { id: 1, title: 'Раздел A', description: 'Базовые курсы', children: [
    { id: 11, title: 'Курс A1', description: '...' },
    { id: 12, title: 'Курс A2', description: '...' },
  ]},
  { id: 2, title: 'Курс без раздела', description: 'Самостоятельный', children: [] },
  { id: 3, title: 'Раздел B', description: '', children: [
    { id: 31, title: 'Курс B1', description: '' },
  ]},
];

export function getCourses() {
  return new Promise(resolve => setTimeout(() => resolve(mockData), 200));
}