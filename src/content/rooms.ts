/**
 * The rooms behind the canal's windows. Each room is a pre-rendered cutaway
 * (public/rooms/<id>/) whose objects stand for parts of a project; the panel
 * beside it tells the project plainly, and each object has one line there.
 *
 * TODO(laia): reword any caption that doesn't sound like you.
 */
export interface RoomSpot {
  /** hotspot group name in public/rooms/<id>/scene.json */
  group: string;
  label: string;
  text: string;
  /** which project tab it belongs to (multi-project rooms); default: all */
  project?: string;
}

export interface Room {
  id: string;
  name: string;
  /** canal building group that opens it */
  building: string;
  /** one tab per project */
  projects: string[];
  /** render variant per project tab (e.g. the gardener on the fire side) */
  variants?: Record<string, string>;
  spots: RoomSpot[];
}

export const rooms: Room[] = [
  {
    id: 'shop',
    name: 'Squirrels and Seeds',
    building: 'shop',
    projects: ['squirrels-and-seeds'],
    spots: [
      { group: 'squirrel', label: 'Where it started', text: 'It grew out of the donation drives I ran, which moved about $50,000 in goods.' },
      { group: 'crates', label: 'In and out', text: 'Every donated item is logged as it comes in and as it goes out.' },
      { group: 'shelves', label: 'On the shelf', text: 'Each organization sees its stock at a glance, and its data stays private to it.' },
      { group: 'counter', label: 'The tool', text: 'A web app nonprofits use to log donated goods. React, TypeScript, PostgreSQL.' },
      { group: 'notes', label: 'Who uses it', text: 'Piloting with 7 local nonprofits.' },
      { group: 'board', label: 'How fast', text: 'Load-tested at 90,000 records; the main stock page went from 4.7 s to 0.22 s.' },
    ],
  },
  {
    id: 'greenhouse',
    name: 'Lilies & Rain, Lilies & Fire',
    building: 'corner',
    projects: ['lily-and-rain', 'lily-and-fire'],
    variants: { 'lily-and-rain': 'room', 'lily-and-fire': 'room-fire' },
    spots: [
      { group: 'rain', label: 'The rain side', text: 'Rain lilies bloom right after rain. This side grows steady, ongoing funding for small governments.', project: 'lily-and-rain' },
      { group: 'fire', label: 'The fire side', text: 'Fire lilies bloom after bushfires. This side grows funding for emergency and disaster preparation.', project: 'lily-and-fire' },
      { group: 'find', label: 'Find', text: 'Find the grants a small town could actually win.' },
      { group: 'decide', label: 'Decide', text: 'Weigh whether one is worth the effort before writing a word.' },
      { group: 'draft', label: 'Draft', text: 'Turn the paperwork a grant needs into an application.' },
      { group: 'review', label: 'Review', text: 'Check it over before it goes out.' },
      { group: 'status', label: 'Where it is', text: 'A seedling: no users yet. First come 8–10 interviews, then the build.' },
      { group: 'gardener', label: 'The gardener', text: 'One gardener tends both sides. Switch tabs to send them over.' },
    ],
  },
];

/** Rooms stay hidden until one of them is good enough to show (?rooms to preview). */
export const ROOMS_ENABLED = typeof location !== 'undefined' && new URLSearchParams(location.search).has('rooms');
export const roomForBuilding = (g: string) => (ROOMS_ENABLED ? rooms.find((r) => r.building === g) ?? null : null);
