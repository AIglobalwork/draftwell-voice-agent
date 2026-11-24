import { REPO_URL } from '@/lib/demo';

// Sections, copy and colors follow the approved design "B. Service van".

const HEADING = 'font-condensed font-extrabold leading-none';
const PRICE = 'font-condensed text-[36px] font-extrabold text-[#F5C518]';

const PRICES = [
  ['Whole-system cleaning, up to 10 vents', '$449'],
  ['Each extra vent', '$35'],
  ['Second system and beyond', '$349'],
  ['Dryer vent cleaning', '$129'],
  ['Blower cleaning, per system', '$179'],
  ['Antimicrobial treatment, per system', '$99'],
];

const STEPS = [
  'We cover floors and furniture near every vent.',
  'Vent covers come off and get washed.',
  'A HEPA vacuum pulls the dust out while brushes loosen it.',
  'We clean the blower and check your filter.',
  'You get before and after photos from inside the ducts.',
];

const EXAMPLE_ROWS = [
  ['Whole system, first 10 vents', '$449'],
  ['4 extra vents × $35', '$140'],
  ['Dryer vent', '$129'],
];

function CallButton({ onStartCall }: { onStartCall: () => void }) {
  return (
    <button
      type="button"
      onClick={onStartCall}
      className="flex min-h-[54px] cursor-pointer items-center gap-2.5 rounded-full bg-[#F5C518] px-7 py-4 text-lg font-bold text-[#1C2124]"
    >
      <svg
        width="20"
        height="20"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.5 2.1L8 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2z" />
      </svg>
      Talk to our AI assistant
    </button>
  );
}

function DemoNote() {
  return (
    <p className="max-w-[28em] text-sm leading-snug text-[#D9E7E4]">
      The live demo runs on free tiers. If it&apos;s paused,{' '}
      <a href={REPO_URL} className="font-semibold !text-white underline">
        see how it works
      </a>{' '}
      on GitHub.
      <span className="mt-1 block">
        Calls are processed by Google Gemini. Please don&apos;t share real personal information.
      </span>
    </p>
  );
}

function ChatBubble({ from, children }: { from: 'agent' | 'caller'; children: React.ReactNode }) {
  const style =
    from === 'agent'
      ? 'rounded-[14px_14px_14px_4px] bg-[#EBEDEC]'
      : 'self-end rounded-[14px_14px_4px_14px] bg-[#0D4A42] text-white';
  return (
    <p className={`m-0 max-w-[88%] px-3.5 py-2.5 text-[15px] leading-[1.45] ${style}`}>
      {children}
    </p>
  );
}

export function SitePage({ onStartCall }: { onStartCall: () => void }) {
  return (
    <div className="bg-white text-[#1C2124]">
      {/* Hero */}
      <section id="top" className="relative overflow-hidden bg-[#0D4A42] text-white">
        <div className="mx-auto flex max-w-[1180px] flex-wrap items-center gap-6 px-8 pt-[22px]">
          <span className="font-condensed mr-auto text-[34px] font-extrabold tracking-[0.5px] italic">
            Draftwell
          </span>
          <nav aria-label="Main" className="flex flex-wrap gap-[22px] text-base font-medium">
            <a href="#prices" className="!text-white">
              Prices
            </a>
            <a href="#visit" className="!text-white">
              How a visit works
            </a>
            <a href="#area" className="!text-white">
              Where we work
            </a>
          </nav>
          <a href="tel:+14045550142" className="text-[17px] font-bold !text-[#F5C518]">
            (404) 555-0142
          </a>
        </div>
        <div className="mx-auto flex max-w-[1180px] flex-wrap items-center gap-14 px-8 pt-16 pb-28">
          <div className="flex min-w-0 flex-[1_1_440px] flex-col gap-6">
            <h1 className="font-condensed m-0 text-[clamp(56px,7.5vw,104px)] leading-[0.92] font-bold tracking-[-0.5px] text-white">
              Call at 9 pm.
              <br />
              Booked by 9:03.
            </h1>
            <p className="m-0 max-w-[30em] text-xl leading-normal text-[#D9E7E4]">
              Duct cleaning in Atlanta, Georgia. Our AI booking assistant answers every call, quotes
              from our price list and puts you on the crew&apos;s calendar.
            </p>
            <div className="flex flex-wrap items-center gap-4">
              <CallButton onStartCall={onStartCall} />
              <a href="#prices" className="px-1 py-3 text-lg font-semibold !text-white">
                See prices
              </a>
            </div>
            <DemoNote />
          </div>
          <div className="flex min-w-0 flex-[0_1_380px] flex-col gap-3 rounded-[22px] bg-white p-[22px] text-[#1C2124] shadow-[0_24px_48px_rgba(0,0,0,0.25)]">
            <div className="flex items-center justify-between border-b border-[#E1E4E3] pb-1.5 text-sm text-[#4D5559]">
              <span className="font-bold text-[#1C2124]">Call in progress</span>
              <span>2:41</span>
            </div>
            <ChatBubble from="agent">
              Draftwell booking assistant. What can we clean for you?
            </ChatBubble>
            <ChatBubble from="caller">
              The ducts and the dryer vent. Two stories, about 14 vents.
            </ChatBubble>
            <ChatBubble from="agent">
              That comes to about $718. Would Thursday 8 to 12 or 1 to 5 work?
            </ChatBubble>
            <ChatBubble from="caller">Thursday morning.</ChatBubble>
            <div className="mt-1 flex flex-col gap-1 rounded-xl border-2 border-[#1C2124] px-3.5 py-3">
              <span className="text-[15px] font-bold">Booked for Thursday, 8 to 12</span>
              <span className="text-sm text-[#4D5559]">
                Estimate $718. Confirmation sent by text.
              </span>
            </div>
          </div>
        </div>
        <div
          aria-hidden="true"
          className="absolute right-0 bottom-0 left-0 h-14 bg-[#F5C518] [clip-path:polygon(0_60%,100%_0,100%_100%,0_100%)]"
        />
      </section>

      {/* Prices */}
      <section
        id="prices"
        className="mx-auto flex max-w-[1180px] flex-wrap items-start gap-12 px-8 py-[72px]"
      >
        <div className="flex flex-[1_1_300px] flex-col gap-3.5">
          <h2 className={`${HEADING} m-0 text-[52px]`}>Straight prices</h2>
          <p className="m-0 max-w-[26em] text-lg leading-[1.55] text-[#3E4649]">
            No &quot;$49 whole house&quot; coupons. You hear an estimate on the call, and the
            technician confirms it before starting.
          </p>
          <div className="mt-2 flex flex-col gap-2.5 rounded-2xl bg-[#EBEDEC] px-6 py-[22px]">
            <span className="text-[17px] font-bold">
              Example: two-story home, 14 vents, dryer vent
            </span>
            {EXAMPLE_ROWS.map(([label, amount]) => (
              <div key={label} className="flex justify-between gap-4 text-base text-[#3E4649]">
                <span>{label}</span>
                <span>{amount}</span>
              </div>
            ))}
            <div className="mt-1 flex items-baseline justify-between gap-4 border-t-2 border-[#1C2124] pt-3">
              <span className="text-lg font-bold">Estimate</span>
              <span className="font-condensed text-[40px] leading-none font-extrabold text-[#0D4A42]">
                $718
              </span>
            </div>
          </div>
        </div>
        <div className="flex-[2_1_560px] rounded-2xl bg-[#1C2124] px-8 py-3 text-white">
          {PRICES.map(([label, price]) => (
            <div
              key={label}
              className="flex items-baseline justify-between gap-4 border-b border-[#3A4245] py-[18px] last:border-b-0"
            >
              <span className="text-[19px]">{label}</span>
              <span className={PRICE}>{price}</span>
            </div>
          ))}
        </div>
      </section>

      {/* How a visit works */}
      <section id="visit" className="bg-[#EBEDEC]">
        <div className="mx-auto flex max-w-[1180px] flex-col gap-8 px-8 py-[72px]">
          <h2 className={`${HEADING} m-0 text-[52px]`}>How a visit works</h2>
          <ol className="m-0 grid list-none grid-cols-[repeat(auto-fit,minmax(200px,1fr))] gap-6 p-0">
            {STEPS.map((step, i) => (
              <li key={step} className="flex flex-col gap-2.5">
                <span className="font-condensed text-5xl leading-none font-extrabold text-[#0D4A42]">
                  {i + 1}
                </span>
                <span className="text-[17px] leading-normal">{step}</span>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* Area, hours, person */}
      <section
        id="area"
        className="mx-auto grid max-w-[1180px] grid-cols-[repeat(auto-fit,minmax(min(300px,100%),1fr))] gap-12 px-8 py-[72px]"
      >
        <div className="flex flex-col gap-3.5">
          <h2 className={`${HEADING} m-0 text-[44px]`}>Where we work</h2>
          <p className="m-0 text-lg leading-[1.55] text-[#3E4649]">
            Atlanta, Decatur, Brookhaven, Sandy Springs, Dunwoody and Smyrna. Give the assistant
            your ZIP code and it checks for you.
          </p>
        </div>
        <div className="flex flex-col gap-3.5">
          <h2 className={`${HEADING} m-0 text-[44px]`}>When we come</h2>
          <p className="m-0 text-lg leading-[1.55] text-[#3E4649]">
            Monday to Saturday, in a morning (8 to 12) or afternoon (1 to 5) window. The assistant
            takes calls around the clock.
          </p>
        </div>
        <div className="flex flex-col gap-3.5">
          <h2 className={`${HEADING} m-0 text-[44px]`}>Rather talk to a person?</h2>
          <p className="m-0 text-lg leading-[1.55] text-[#3E4649]">
            Say so on the call. The assistant takes a message and the owner calls you back.
          </p>
        </div>
      </section>

      {/* Closing band */}
      <section className="bg-[#0D4A42] text-white">
        <div className="mx-auto flex max-w-[1180px] flex-col items-start gap-5 px-8 py-[72px]">
          <h2 className={`${HEADING} m-0 text-[52px]`}>Ready when you are.</h2>
          <CallButton onStartCall={onStartCall} />
          <DemoNote />
        </div>
      </section>

      <footer className="bg-[#1C2124] text-[#C9CFD1]">
        <div className="mx-auto flex max-w-[1180px] flex-wrap justify-between gap-4 px-8 py-7 text-sm">
          <span>
            Draftwell is a fictional company. This site demonstrates an AI booking assistant.
          </span>
          <span>(404) 555-0142</span>
        </div>
      </footer>
    </div>
  );
}
