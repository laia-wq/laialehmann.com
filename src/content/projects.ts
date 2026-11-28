/**
 * All site content lives here. To add a project, add an entry to `projects`.
 *
 * `object` picks the miniature that represents the project inside the globe
 * (see src/three/objects). Projects without a 3D object still appear in the
 * 2D index and the keyboard list.
 *
 * Anything wrapped in TODO(laia) is a placeholder waiting for real material.
 */

export type ProjectStatus = 'shipped' | 'in-progress' | 'team' | 'community';

export interface ProjectLink {
  label: string;
  href: string;
}

export interface ProjectMedia {
  /** Path under /public, or null while the real asset is missing. */
  src: string | null;
  alt: string;
  caption?: string;
}

export interface Project {
  id: string;
  title: string;
  status: ProjectStatus;
  /** One line, shown under the title. */
  summary: string;
  /** Short paragraphs for the panel. */
  body: string[];
  /** Concrete, verified results. */
  highlights?: string[];
  stack?: string[];
  links?: ProjectLink[];
  media?: ProjectMedia[];
  /** Key of the 3D miniature. */
  object?: string;
}

export const statusLabel: Record<ProjectStatus, string> = {
  shipped: 'Built',
  'in-progress': 'In progress',
  team: 'Design team',
  community: 'Community',
};

export const projects: Project[] = [
  {
    id: 'squirrels-and-seeds',
    title: 'Squirrels and Seeds',
    status: 'shipped',
    summary: 'Inventory for nonprofits: donated goods in, out and on the shelf.',
    body: [
      'Squirrels and Seeds grew out of the donation drives I ran, which moved about $50,000 in goods. Keeping track of what came in, what went out and what was still on the shelf was the hard part, so I built a tool for it.',
      'It is a web app that nonprofits use to log donated goods and see their stock at a glance. Each organization’s data is kept private to that organization.',
    ],
    highlights: [
      'Piloting with 7 local nonprofits',
      'Load-tested at 90,000 records',
      'Main stock page: 4.7 s → 0.22 s',
    ],
    stack: ['React', 'TypeScript', 'PostgreSQL'],
    media: [
      {
        src: null,
        alt: 'Screenshot of the Squirrels and Seeds stock page',
        caption: 'TODO(laia): screenshot of the stock page',
      },
    ],
    object: 'acorn',
  },
  {
    id: 'signwise',
    title: 'Signwise',
    status: 'shipped',
    summary: 'An ASL alphabet coach that runs entirely in your browser.',
    body: [
      'Signwise watches your hand through the webcam and coaches you through the ASL alphabet. No video leaves the device.',
      'It tracks 21 3D hand landmarks per frame and scores handshapes A–Z and ILY, including the motion-based J and Z. Instead of a pass/fail it gives targeted corrections, like “curl index finger”.',
    ],
    highlights: ['21 hand landmarks per frame', 'A–Z plus ILY, including motion-based J and Z'],
    stack: ['JavaScript', 'Google MediaPipe'],
    links: [{ label: 'Try it live', href: 'https://laia-wq.github.io/signwise' }],
    object: 'hand',
  },
  {
    id: 'forest-loss',
    title: 'Forest Loss Detection',
    status: 'shipped',
    summary: 'Mapping pixel-level forest loss from satellite imagery.',
    body: [
      'A 6-band Siamese U-Net compares 2018 and 2025 Sentinel-2 imagery of the same place and marks, pixel by pixel, where forest was lost. It is trained against Hansen Global Forest Change labels.',
    ],
    highlights: ['Training data scaled 5.9×', 'F1 improved 16× on an unseen region', 'Gradio demo'],
    stack: ['Python', 'Siamese U-Net', 'Sentinel-2'],
    links: [{ label: 'Code on GitHub', href: 'https://github.com/laia-wq/forest-loss-detection' }],
    object: 'forest',
  },
  {
    id: 'physics-engine',
    title: '2D Physics Engine & Wireframe Lab',
    status: 'shipped',
    summary: 'A from-scratch C++17 engine. The snow in this globe borrows its ideas.',
    body: [
      'Written from scratch in C++17 with SFML: a 120 Hz fixed step, impulse collisions, tearing springs, electrostatics and force fields.',
      'A uniform-grid broad phase cut collision candidate pairs from 499,500 to 1,957 at 1,000 particles, making it 2.62× faster. Released as v1.0.0 with CTest suites and CI.',
    ],
    highlights: ['499,500 → 1,957 candidate pairs at 1,000 particles', '2.62× faster', 'v1.0.0 with CTest and CI'],
    stack: ['C++17', 'SFML', 'CTest'],
    links: [{ label: 'Code on GitHub', href: 'https://github.com/laia-wq/physics-engine' }],
    object: 'snow',
  },
  {
    id: 'bridgeway',
    title: 'Bridgeway',
    status: 'shipped',
    summary: 'UWPM ProdCon case competition: a lecture companion, shipped in one day.',
    body: [
      'Built in a single day for first-year students with learning differences. During a lecture you flag where you got lost, get an AI explanation at the depth you choose, then practise.',
      'Instructors only see anonymized trends, never individual students.',
    ],
    object: 'bridge',
  },
  {
    id: 'lily-and-rain',
    title: 'Lily and Rain',
    status: 'in-progress',
    summary: 'Helping small governments get funding they couldn’t afford to apply for.',
    body: [
      'Small governments often miss out on funding simply because applying costs more than they can spend. Lily and Rain is about closing that gap, with a focus on consistent, ongoing funding.',
    ],
    object: 'raindrop',
  },
  {
    id: 'lily-and-fire',
    title: 'Lily and Fire',
    status: 'in-progress',
    summary: 'The same idea, for emergency and natural-disaster preparation.',
    body: [
      'A sibling to Lily and Rain, focused on funding for preparing for emergencies and natural disasters.',
    ],
    object: 'flame',
  },
  {
    id: 'watif',
    title: 'Waterloo API + WatIf',
    status: 'in-progress',
    summary: 'An API for Waterloo deadlines and requirements, and an app built on it.',
    body: [
      'The Waterloo API gathers deadlines and requirements in one place. WatIf sits on top of it and helps students figure out what they want to do long-term.',
      'I hope to present it to Waterloo and get it adopted.',
    ],
    object: 'compass',
  },
  {
    id: 'brita-robot',
    title: 'Sink-finding robot',
    status: 'in-progress',
    summary: 'Real hardware that finds a sink and fills your Brita filter.',
    body: ['A robot that finds the sink on its own and fills your Brita filter.'],
    object: 'droplet',
  },
  {
    id: 'saas',
    title: 'SaaS from scratch',
    status: 'in-progress',
    summary: 'A SaaS model built from the ground up.',
    body: ['A software-as-a-service product built from the ground up.'],
    object: 'blocks',
  },
  {
    id: 'wrl',
    title: 'Waterloo Reality Labs',
    status: 'team',
    summary: 'Firmware: bringing up an IMU over SPI on a Qualcomm RB5.',
    body: ['On the firmware team, bringing up an IMU over SPI on a Qualcomm RB5.'],
    stack: ['Firmware', 'SPI', 'Qualcomm RB5'],
    object: 'chip',
  },
  {
    id: 'warg',
    title: 'WARG',
    status: 'team',
    summary: 'Autonomous drone vision and geolocation.',
    body: ['Working on vision and geolocation for autonomous drones. WARG is a 2× AEAC national champion.'],
    object: 'drone',
  },
  {
    id: 'medtechresolve',
    title: 'MedTechResolve',
    status: 'team',
    summary: 'Detecting swimmers in distress with YOLO26n.',
    body: ['Building swimmer drowning detection with YOLO26n.'],
    stack: ['YOLO26n'],
    object: 'swimmer',
  },
  {
    id: 'community',
    title: 'Community',
    status: 'community',
    summary: 'Cooking free meals, a youth council, the library, two donation drives.',
    body: [
      'I volunteer as a cook, making and serving free meals.',
      'I am a member of the Youth Council for the Office of MLA Bowinn Ma, and I volunteer at the library.',
      'I founded and ran two donation drives that collected about $50,000 in goods for libraries, Indigenous schools, shelters and families.',
    ],
  },
  {
    id: 'donation-drives',
    title: 'Donation Drives',
    status: 'community',
    summary: 'Founder. Two drives, about $50,000 in goods.',
    body: [
      'I founded and ran two donation drives that collected about $50,000 in goods for libraries, Indigenous schools, shelters and families.',
    ],
    object: 'box',
  },
  {
    id: 'youth-council',
    title: 'Youth Council',
    status: 'community',
    summary: 'Member, Office of MLA Bowinn Ma.',
    body: ['Member of the Youth Council for the Office of MLA Bowinn Ma.'],
  },
  {
    id: 'physics-olympics',
    title: 'UBC Physics Olympics',
    status: 'community',
    summary: 'Team lead. A concave-mirror light design, top 10 of 30+ schools.',
    body: ['Led our team’s concave-mirror light design, placing in the top 10 of more than 30 schools.'],
    object: 'mirror',
  },
];

export const person = {
  name: 'Laia Lehmann',
  role: 'Systems Design Engineering',
  intro:
    'Incoming Honours Systems Design Engineering student at the University of Waterloo, starting September 2026. I work across software, applied ML and hardware, and on community and nonprofit projects.',
  languages: ['Python', 'C++17', 'JavaScript / TypeScript', 'React', 'Node', 'HTML / CSS', 'SQL'],
  spoken: ['English', 'French (DALF C1)', 'Spanish', 'Catalan'],
  // From the 2026 résumé. Never add the phone number here.
  contact: [
    { label: 'LinkedIn', href: 'https://www.linkedin.com/in/laia-lehmann-5274a6334' },
    { label: 'Email', href: 'mailto:laia.lehmanngimenez@gmail.com' },
    { label: 'GitHub', href: 'https://github.com/laia-wq' },
  ] as ProjectLink[],
  /** Home page phrase: greeting, then "I build for <em>…</em>". */
  greeting: 'bona nit,',
  phraseLead: 'I build for',
  phraseEm: 'the overlooked.',
  tagLeft: 'systems design engineering',
  tagRight: 'recently: syde @uwaterloo',
  invite: {
    word: 'sonder',
    definition: 'the realization that each passerby has a life as vivid and complex as your own.',
    window: "it's like looking through someone's window; you only see a fraction of their world, but behind each window, you understand there is a life as full as yours.",
    me: 'i have lived everywhere, knowing neither the culture nor the language, but nothing made me see just how little i know like building did. look through the yellow windows with me.',
  },
  /** Top of the About sheet: why the site is a street of windows. */
  sonder: {
    word: 'sonder',
    definition: 'the realization that each passerby has a life as vivid and complex as your own.',
    windows: 'Walk past lit windows at night and you feel it: behind every one is a whole world you only get to glimpse.',
    projects: "Every project I take on is like that. It's a brand new window, a chance to see a problem from someone else's side of the glass.",
  },
  scholarships: ["President's Scholarship of Distinction", 'Joyce A. Borrie and George W. Stevenson Memorial Scholarship'],
};
