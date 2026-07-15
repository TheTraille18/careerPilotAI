import type { AppStatus } from '../theme/ablackcloud';

export interface ToolGroup {
  category: string;
  tools: string[];
}

export interface ProgressUpdate {
  date: string;
  title: string;
  detail: string;
}

export interface ShowcaseContent {
  title: string;
  tagline: string;
  status: AppStatus;
  summary: string[];
  toolsUsed: ToolGroup[];
  progressUpdates: ProgressUpdate[];
}

export const careerPilotContent: ShowcaseContent = {
  title: 'CareerPilot AI',
  tagline:
    'Pull job alerts from Gmail, parse LinkedIn, Dice, and Indeed listings, and surface the best-fit roles for your profile.',
  status: 'In Development',
  summary: [
    'CareerPilot AI connects to Gmail and reads job alert emails from LinkedIn, Dice, and Indeed. Each alert is parsed into structured listings with job title, company, location, and date.',
    'A FastAPI backend wraps the Python parsers and exposes jobs to this React dashboard. The next phase adds profile-aware AI scoring so you can focus on the highest-match opportunities first.',
    'Deduplicated listings and Bedrock-powered fit scoring are planned next.',
  ],
  toolsUsed: [
    { category: 'Frontend', tools: ['React', 'TypeScript', 'Vite'] },
    { category: 'Backend', tools: ['Python', 'FastAPI', 'Gmail API', 'BeautifulSoup', 'DynamoDB'] },
    { category: 'Sources', tools: ['LinkedIn alerts', 'Dice alerts', 'Indeed alerts'] },
    { category: 'Planned', tools: ['Bedrock scoring', 'Profile YAML'] },
  ],
  progressUpdates: [
    {
      date: 'Jul 12, 2026',
      title: 'Indeed job alerts',
      detail:
        'Added an Indeed parser for label:jobs-indeed and wired it into the CLI, API, and React source filters alongside LinkedIn and Dice.',
    },
    {
      date: 'Jul 11, 2026',
      title: 'React dashboard + API',
      detail:
        'Added a FastAPI /api/jobs endpoint and a TypeScript React UI that lists parsed LinkedIn and Dice alerts with source filters.',
    },
    {
      date: 'Jul 11, 2026',
      title: 'Dice + LinkedIn parsers',
      detail:
        'Built separate parser modules for LinkedIn table rows and Dice job cards, extracting title, company, location, and posted date from HTML emails.',
    },
    {
      date: 'Jul 11, 2026',
      title: 'Gmail OAuth',
      detail:
        'Connected Gmail read-only access and labeled inbox filters for jobs-linkedin, jobs-dice, and jobs-indeed.',
    },
  ],
};
