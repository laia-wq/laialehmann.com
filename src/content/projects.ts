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
    title: "Squirrels & Seeds",
    status: "in-progress",
    summary: "A web app where small nonprofits track donations, stock and drives.",
    body: [
      "Small nonprofits run on donations, and volunteers do much of the tracking. I'm piloting this with seven local ones, including Mamas for Mamas, Kinbridge and Food4Kids Waterloo Region. Most had little or only basic tracking. So “what's running low?” or “what were these donations worth?” had no easy answer, especially when a funder asked.",
      "Teams can log donations in and items out, watch stock against minimums, run drives with pledges, and see supporters and estimated worth. All nonprofits share one database, kept apart by row-level security. Stock loads fast because each movement updates a running balance, instead of re-adding the whole history on every page load.",
      "The hard part was demoing it. Early on I couldn't get my ideas across, so I let the tool speak for itself. Over more interviews I learned which parts to show, in what order, and which questions nonprofits ask. Now my talking helps the demo instead of getting in its way.",
    ],
    highlights: [
      "7 local nonprofits are piloting it: Mamas for Mamas, Kinbridge, Food4Kids Waterloo Region, oneROOF Youth Services, FACS Foundation, Hope House Guelph, and the KW & SP Humane Society",
      "Stock list loads in 0.22 seconds with 90,000 records, after I added indexes and running balances (my benchmark on an example organization, not live data)",
    ],
    stack: ["React 18", "TypeScript", "Vite", "Supabase (Postgres, row-level security)", "Cloudflare Pages"],
    links: [
      { label: "GitHub", href: "https://github.com/laia-wq/squirrels-and-seeds" },
      { label: "Live site", href: "https://squirrelsandseeds.com" },
    ],
    object: "acorn",
  },
  {
    id: 'signwise',
    title: "Signwise",
    status: "shipped",
    summary: "A webcam coach for practicing the ASL alphabet, letter by letter.",
    body: [
      "I wanted to learn the ASL alphabet, but a diagram can't tell you your thumb is in the wrong place. Signwise is for beginners like me, practicing fingerspelling alone, who need something to say what's off.",
      "You make a letter at your webcam and it tells you what to fix, like “curl index finger.” It tracks 21 points on your hand and checks each letter as a set of geometric rules, so when one rule fails, it can name the finger. Everything runs in the browser, so no video leaves your computer.",
      "The hard part was strictness. Too loose, and wrong shapes pass. Too strict, and correct ones fail. One reviewer sent screenshots where my A scored 100 with the thumb sticking out. I added checks for where the thumb touches and points. It's still experimental and hasn't been tested with fluent signers.",
    ],
    highlights: [
      "Live and free to use, covering A to Z plus “I love you”, including the moving letters J and Z",
      "Reworked A and S, then J and Z, after feedback from two outside reviewers",
    ],
    stack: ["JavaScript (ES modules)", "HTML", "CSS", "MediaPipe Hand Landmarker", "Node test runner", "GitHub Pages", "GitHub Actions"],
    links: [
      { label: "Live demo", href: "https://laia-wq.github.io/signwise/" },
      { label: "GitHub", href: "https://github.com/laia-wq/signwise" },
      { label: "LinkedIn post", href: "https://www.linkedin.com/feed/update/urn:li:activity:7516558611482079232/" },
    ],
    object: "hand",
  },
  {
    id: 'forest-loss',
    title: "Forest Loss Detection from Satellite Imagery",
    status: "shipped",
    summary: "My first machine-learning model: it maps forest loss between 2018 and 2025.",
    body: [
      "Forest loss is easy to talk about and hard to see. I wanted a way to compare the same land in 2018 and 2025 and see where trees were lost. My first model, a land-use classifier, scored 94.7% in testing but missed much of the real loss.",
      "I switched to a model built for change. It reads both years through one shared encoder, so it compares like with like, and marks each pixel that lost forest. In the demo, you pick a region and a patch and see both years, the reference map, the prediction and its mistakes.",
      "My first version scored 0.70 F1 on validation, then found almost nothing in Greece, an unseen region. I grew the data from 6 regions to 30 and weighted the loss to punish misses. Greece F1 rose from 0.03 to 0.40. It works, partly: one threshold still doesn't fit every landscape.",
    ],
    highlights: [
      "On Greece, a region the model never trained on, F1 rose from 0.025 to 0.399 and recall from 0.012 to 0.254",
      "Tested once on 3 regions kept out of training and tuning: macro F1 0.35, with Chile the best at 0.54 F1 and 0.79 recall",
      "Grew the training data 5.9×, to 10,303 patches from 30 regions worldwide",
    ],
    stack: ["Python", "PyTorch", "Torchvision", "Rasterio", "Google Earth Engine", "Sentinel-2", "Hansen Global Forest Change", "Gradio", "NVIDIA DGX Spark"],
    links: [
      { label: "GitHub", href: "https://github.com/laia-wq/forest-loss-detection" },
    ],
    object: "forest",
  },
  {
    id: 'physics-engine',
    title: "2D Physics Engine & Wireframe Art",
    status: "shipped",
    summary: "A 2D physics engine I wrote from scratch that turned into wireframe art.",
    body: [
      "Physics libraries usually hide the math. I wanted to see what happens inside one, so I built a 2D engine from scratch in C++, using SFML only to draw. I built it for me first, then for anyone who learns by poking at things.",
      "You can throw particles, add wind or a vortex, and pull on a spring mesh until it tears. As the meshes grew, they started to look like drawings, so I added wireframe scenes: an apple, a windblown tree, a hillside city. I kept physics, scene building and drawing separate, so the physics can be tested without opening a window.",
      "The heaviest scene dropped to 4 frames per second. Each physics step took longer than its 8 ms slot, and the engine kept trying to catch up, which put it further behind. I capped it at two steps per frame and dropped the backlog, so it stays responsive.",
    ],
    highlights: [
      "At 1,000 particles, a spatial grid cut 499,500 possible collision pairs to 1,957 and found the same contacts 2.62× faster than checking every pair",
      "Released v1.0.0 as a downloadable app for Apple-silicon Macs",
      "10 automated test suites and a benchmark check run on every push through GitHub Actions",
    ],
    stack: ["C++17", "SFML 3", "Dear ImGui (ImGui-SFML)", "CMake", "CTest", "GitHub Actions"],
    links: [
      { label: "GitHub", href: "https://github.com/laia-wq/physics-engine" },
      { label: "macOS app", href: "https://github.com/laia-wq/physics-engine/releases" },
      { label: "Video", href: "https://www.linkedin.com/feed/update/urn:li:activity:7505786197143703553/" },
    ],
    media: [
      { src: "projects/physics/cloth-tear.webp", alt: "A spring mesh being pulled until it starts to tear" },
      { src: "projects/physics/apple.webp", alt: "A wireframe apple built from a spring mesh" },
      { src: "projects/physics/vortex.webp", alt: "Glowing particles spiralling into a vortex, leaving trails" },
      { src: "projects/physics/wave.webp", alt: "A wireframe sheet rippling in waves" },
      { src: "projects/physics/torus.webp", alt: "A wireframe torus" },
    ],
    object: "snow",
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
    title: "Lilies & Rain",
    status: "in-progress",
    summary: "A planned tool that helps small towns find and apply for funding.",
    body: [
      "Small towns, townships and First Nations often miss funding they qualify for. A village of 500 has one clerk, no grant writer and no time to read a 40-page program guide. I've talked with people who work in local government to test this.",
      "In my design, a clerk types what the town needs, like a failing culvert. The tool shows a short list of programs that fit, marks ones with a match the town can't cover, and drafts an application from the town's own budget and minutes. A person reviews every draft. The home screen is a lily bulb in cross-section. The roots are documents on file, and the flower is the application.",
      "The hard part is that the research proves the problem, not the fix. One First Nations study blames forms and process, not software. So I'm testing by hand with a few towns before I build. Today it is a design and a plan.",
    ],
    stack: ["HTML", "CSS", "SVG"],
    object: "raindrop",
  },
  {
    id: 'lily-and-fire',
    title: "Lilies & Fire",
    status: "in-progress",
    summary: "A planned tool that gets small towns ready for disaster funding before a disaster.",
    body: [
      "When a flood or wildfire hits a small town, the same clerk who runs everything faces tight deadlines and a pile of recovery paperwork. Larger places have staff for this, and small ones don't. I've talked with people who work in local government about this.",
      "In my design, the work happens before the disaster. A town keeps its asset list, maps, insurance and budget in one place. After a disaster, the tool turns that file into the damage records recovery programs ask for, so a clerk starts from a full folder, not a blank page. I borrowed the idea from the fire lily, whose bulb is stored underground and blooms days after a fire.",
      "The open question is that nobody wants to prepare for a disaster that hasn't happened. A tool that matters once a decade is hard to keep current, so I'm working out how to make the preparation useful on ordinary days. Today it is an idea and a design direction, nothing built.",
    ],
    object: "flame",
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
    title: "Firmware for a VR Headset's Motion Sensor",
    status: "team",
    summary: "Connecting a motion sensor to a VR headset's Linux board.",
    body: [
      "I did firmware for a standalone VR headset at Waterloo Reality Labs, a student team. It is for the people who wear it and the teammates building its head tracking. It has to know the moment your head turns. A small motion sensor measures that, but on our Qualcomm RB5 board it had to be wired up, and Linux had to be told it existed.",
      "I worked with a teammate to finish every step on the task list for the sensor. I wired it to the board, then described it in the device tree, the file Linux reads at boot to learn what hardware is attached. If the pins in the file differ from the wires, the sensor stays silent. The sensor now answers its ID check.",
      "The hard part was that we had no written device-tree guide, and it was not settled which board pins the sensor could use.",
    ],
    highlights: [
      "The sensor answers its ID check on the RB5 board.",
    ],
    stack: ["Embedded Linux", "Device tree", "SPI", "Qualcomm RB5 board", "ST LSM6DSV16X motion sensor"],
    object: "chip",
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
    title: "Community Work in North Vancouver",
    status: "community",
    summary: "A donation drive, a youth housing council, and monthly community dinners.",
    body: [
      "In North Vancouver I kept meeting people stretched thin: families who couldn't afford good everyday things, and young people who expected to leave because they'd never afford a home.",
      "I started a weekly donation drive. I sorted the items and took them where they fit: books to public libraries, food to under-funded Indigenous schools, and the best things to a free open drive where families chose what they wanted. On MLA Bowinn Ma's Youth Council, I helped survey young people on housing and drafted policy recommendations. Once a month I cooked a multi-course dinner for over 100 guests at my high school.",
      "The first person at the drive had lost her home in a fire. I let her look through everything privately. It didn't change her life, but it made a hard stretch easier, so I ran the drive a second year and showed volunteers how.",
    ],
    highlights: [
      "About $50,000 worth of donated items collected",
      "Youth Council housing survey with hundreds of responses",
      "Cooked monthly community dinners from Sept 2023 to May 2026",
    ],
    stack: ["Survey design", "Policy research", "Logistics", "Foodsafe Level 1"],
  },
  {
    id: 'wusa',
    title: "At-Large Member, WUSA Advocacy Committee",
    status: "community",
    summary: "I help decide what Waterloo's student union asks the university to change.",
    body: [
      "Most Waterloo undergrads never sit in a student union meeting, but WUSA's positions speak for them to the university and the province. I'm one of three at-large members on its Advocacy Committee. I don't represent a faculty or society, so my job is to bring in what everyday students are dealing with.",
      "Before a position goes to the Board of Directors, we read it, question it and vote. In October we voted on WUSA's environmental sustainability position. It draws on a student survey where 91% wanted the university to act, and many felt their own efforts were tiny next to institutions. So it asks the university to fix systems, like composting and investments, instead of putting the weight on students.",
      "I voted for it. Most students in the survey weren't sure whether the university was doing enough, which suggests part of the problem is that nobody hears about the work. I'm two months in.",
    ],
    highlights: [
      "Selected as one of three at-large members on the Advocacy Committee (Oct 2026)",
      "Voted for WUSA's environmental sustainability position at the October 29 committee meeting",
      "Committee topics this term have included campus sustainability and student feedback on AccessAbility Services",
    ],
    stack: ["Policy review", "Student survey data", "Committee voting", "Public speaking"],
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
    window: "like looking through a stranger's window; you only see a fraction of their world, but behind each window, you understand there is a life as full as yours.",
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
