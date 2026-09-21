import { useMemo, useRef, useState } from 'react';
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  ChevronRight,
  Landmark,
  X,
} from 'lucide-react';

type CustomerId = 'marcus' | 'dana' | 'james' | 'tanya' | 'keith';

type Customer = {
  id: CustomerId;
  name: string;
  role: string;
  loanType: string;
  description: string;
  photo: string;
  riskTier: string;
  features: string[];
  glyph: string;
  baseLoanAmount: number;
  baseExposure: number;
};

const CAP = 5_000_000;

const customers: Customer[] = [
  {
    id: 'marcus',
    name: 'Marcus Bell',
    role: 'Digital Personal Loan',
    loanType: 'Unsecured · Fixed rate',
    description: 'A fully digital unsecured personal loan with instant pre-qualification and same-day funding decisions.',
    photo: 'https://images.pexels.com/photos/12311537/pexels-photo-12311537.jpeg?auto=compress&cs=tinysrgb&h=650&w=940',
    riskTier: 'Prime',
    features: ['Instant pre-qualification', 'Same-day funding', 'No collateral required'],
    glyph: 'I',
    baseLoanAmount: 1_200_000,
    baseExposure: 800_000,
  },
  {
    id: 'dana',
    name: 'Dana Carter',
    role: 'Digital Personal Loan',
    loanType: 'Unsecured · Fixed rate',
    description: 'A fully digital unsecured personal loan with instant pre-qualification and same-day funding decisions.',
    photo: 'https://images.pexels.com/photos/9304685/pexels-photo-9304685.jpeg?auto=compress&cs=tinysrgb&h=650&w=940',
    riskTier: 'Standard',
    features: ['Instant pre-qualification', 'Same-day funding', 'No collateral required'],
    glyph: 'II',
    baseLoanAmount: 2_500_000,
    baseExposure: 1_500_000,
  },
  {
    id: 'james',
    name: 'James Foster',
    role: 'Digital Personal Loan',
    loanType: 'Unsecured · Fixed rate',
    description: 'A fully digital unsecured personal loan with instant pre-qualification and same-day funding decisions.',
    photo: 'https://images.pexels.com/photos/7446948/pexels-photo-7446948.jpeg?auto=compress&cs=tinysrgb&h=650&w=940',
    riskTier: 'Near-prime',
    features: ['Instant pre-qualification', 'Same-day funding', 'No collateral required'],
    glyph: 'III',
    baseLoanAmount: 3_000_000,
    baseExposure: 1_800_000,
  },
  {
    id: 'tanya',
    name: 'Tanya Reed',
    role: 'Digital Personal Loan',
    loanType: 'Unsecured · Fixed rate',
    description: 'A fully digital unsecured personal loan with instant pre-qualification and same-day funding decisions.',
    photo: 'https://images.pexels.com/photos/7468194/pexels-photo-7468194.jpeg?auto=compress&cs=tinysrgb&h=650&w=940',
    riskTier: 'Prime',
    features: ['Instant pre-qualification', 'Same-day funding', 'No collateral required'],
    glyph: 'IV',
    baseLoanAmount: 1_800_000,
    baseExposure: 2_200_000,
  },
  {
    id: 'keith',
    name: 'Keith Shaw',
    role: 'Digital Personal Loan',
    loanType: 'Unsecured · Fixed rate',
    description: 'A fully digital unsecured personal loan with instant pre-qualification and same-day funding decisions.',
    photo: 'https://images.pexels.com/photos/8044097/pexels-photo-8044097.jpeg?auto=compress&cs=tinysrgb&h=650&w=940',
    riskTier: 'Near-prime',
    features: ['Instant pre-qualification', 'Same-day funding', 'No collateral required'],
    glyph: 'V',
    baseLoanAmount: 3_500_000,
    baseExposure: 900_000,
  },
];

function formatMoney(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value}`;
}

function randomExposure(maxExposure: number): number {
  return Math.round((Math.random() * maxExposure) / 50_000) * 50_000;
}

function App() {
  const [selectedId, setSelectedId] = useState<CustomerId>('james');
  const [modalCustomer, setModalCustomer] = useState<Customer | null>(null);
  const [loanAmount, setLoanAmount] = useState<number>(2_000_000);
  const [exposure, setExposure] = useState<number>(0);

  const selected = useMemo(
    () => customers.find((customer) => customer.id === selectedId) ?? customers[2],
    [selectedId],
  );
  const selectedIndex = customers.findIndex((customer) => customer.id === selectedId);

  const selectByIndex = (index: number) => {
    const nextIndex = (index + customers.length) % customers.length;
    setSelectedId(customers[nextIndex].id);
  };

  const openModal = (customer: Customer) => {
    const maxExposure = Math.min(3_500_000, CAP - customer.baseLoanAmount);
    const randomizedExposure = randomExposure(maxExposure);
    setLoanAmount(customer.baseLoanAmount);
    setExposure(randomizedExposure);
    setModalCustomer(customer);
  };

  const handleLoanAmountChange = (value: number) => {
    const clamped = Math.min(value, CAP - exposure);
    setLoanAmount(clamped);
  };

  const touchStartX = useRef<number | null>(null);

  const handleTouchStart = (e: React.TouchEvent) => {
    touchStartX.current = e.touches[0].clientX;
  };

  const handleTouchEnd = (e: React.TouchEvent) => {
    if (touchStartX.current === null) return;
    const delta = e.changedTouches[0].clientX - touchStartX.current;
    if (Math.abs(delta) > 40) {
      selectByIndex(selectedIndex + (delta < 0 ? 1 : -1));
    }
    touchStartX.current = null;
  };

  const totalExposure = loanAmount + exposure;
  const loanPct = (loanAmount / CAP) * 100;
  const exposurePct = (exposure / CAP) * 100;

  const continueWithCustomer = () => {
    if (!modalCustomer) return;

    const params = new URLSearchParams({
      customer: modalCustomer.id,
      loanAmount: String(loanAmount),
    });
    window.location.assign(`/application/?${params.toString()}`);
  };

  return (
    <main className="game-shell">
      <div className="grain" aria-hidden="true" />
      <div className="top-rule" aria-hidden="true" />
      <header className="site-header">
        <div className="crest" aria-label="Meridian Bank crest">
          <Landmark size={18} strokeWidth={1.6} />
        </div>
        <div className="brand-lockup">
          <span className="brand-kicker">MERIDIAN</span>
          <span className="brand-name">PRIVATE BANK</span>
        </div>
        <div className="header-status"><span className="status-dot" /> Loan application</div>
        <button className="sound-button" type="button" aria-label="Notifications"><CheckCircle2 size={17} /></button>
      </header>

      <section className="creation-stage" aria-labelledby="page-title">
        <div className="breadcrumb"><span>Loan application</span><ChevronRight size={14} /><strong>Select your customer</strong></div>
        <div className="title-row">
          <div>
            <p className="eyebrow">Step 02 · Loan selection</p>
            <h1 id="page-title">Choose your <em>customer</em></h1>
            <p className="intro">Select the applicant profile that best matches your loan product. Tap a card to view details.</p>
          </div>
          <div className="progress-mark"><span>02</span><i /> <span>04</span><small>your application</small></div>
        </div>

        <div
          className="selection-layout"
          onTouchStart={handleTouchStart}
          onTouchEnd={handleTouchEnd}
        >
          <button className="carousel-arrow left" type="button" onClick={() => selectByIndex(selectedIndex - 1)} aria-label="Previous customer"><ArrowLeft size={19} /></button>
          <div className="card-rail" aria-label="Customer choices">
            {customers.map((customer, index) => {
              const distance = index - selectedIndex;
              const isSelected = customer.id === selectedId;
              return (
                <button
                  className={`class-card ${isSelected ? 'selected' : ''} distance-${Math.abs(distance)}`}
                  key={customer.id}
                  type="button"
                  onClick={() => openModal(customer)}
                  aria-pressed={isSelected}
                >
                  <span className="card-topline"><span>{customer.glyph}</span><span>{isSelected ? 'Selected' : 'View'}</span></span>
                  <span className="card-art">
                    <img className="card-photo-img" src={customer.photo} alt={customer.name} loading="lazy" />
                    <span className="card-photo-overlay" />
                    <span className="card-star star-one">✦</span><span className="card-star star-two">·</span>
                  </span>
                  <span className="card-name">{customer.name}</span>
                  <span className="card-subtitle">{customer.loanType}</span>
                  <span className="card-edge" />
                </button>
              );
            })}
          </div>
          <button className="carousel-arrow right" type="button" onClick={() => selectByIndex(selectedIndex + 1)} aria-label="Next customer"><ArrowRight size={19} /></button>
        </div>

        <div className="select-hint">
          <button className="confirm-button" type="button" onClick={() => openModal(selected)}>
            View {selected.name.split(' ')[0]}'s profile <ArrowRight size={17} />
          </button>
        </div>
      </section>
      <footer className="site-footer"><span>© 2024 Meridian Private Bank</span><span>Equal Housing Lender · NMLS #482719</span><span className="footer-mark"><Landmark size={14} /> MPB</span></footer>

      {modalCustomer && (
        <div className="modal-overlay" onClick={() => setModalCustomer(null)} role="dialog" aria-modal="true">
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" type="button" onClick={() => setModalCustomer(null)} aria-label="Close"><X size={20} /></button>
            <div className="modal-header">
              <img className="modal-avatar" src={modalCustomer.photo} alt={modalCustomer.name} loading="lazy" />
              <div>
                <p className="eyebrow">Selected customer</p>
                <h2>{modalCustomer.name}</h2>
                <p className="details-role">{modalCustomer.role}</p>
              </div>
            </div>
            <p className="details-description">{modalCustomer.description}</p>
            <div className="trait-list">{modalCustomer.features.map((feature) => <span key={feature}><span className="trait-check">✓</span>{feature}</span>)}</div>

            <div className="modal-stats">
              <div className="stat-meta"><span>Loan profile</span><span>Digital · Unsecured</span></div>

              <div className="stat-row stat-row-slider">
                <span>Loan amount</span>
                <div className="slider-wrap">
                  <input
                    type="range"
                    min={0}
                    max={CAP - exposure}
                    step={50_000}
                    value={loanAmount}
                    onChange={(e) => handleLoanAmountChange(Number(e.target.value))}
                    className="loan-slider"
                    aria-label="Loan amount"
                  />
                  <div className="slider-track-bg">
                    <div className="slider-track-fill" style={{ width: `${loanPct}%` }} />
                  </div>
                </div>
                <strong>{formatMoney(loanAmount)}</strong>
              </div>

              <div className="stat-row">
                <span>Unsecured exposure</span>
                <div className="stat-track"><i style={{ width: `${exposurePct}%` }} /></div>
                <strong>{formatMoney(exposure)}</strong>
              </div>

              <div className="stat-row stat-row-total">
                <span>Total exposure</span>
                <div className="stat-track"><i style={{ width: `${(totalExposure / CAP) * 100}%` }} /></div>
                <strong>{formatMoney(totalExposure)}</strong>
              </div>

              <div className="cap-hint">
                <span>Cap: {formatMoney(CAP)}</span>
                <span className={totalExposure > CAP ? 'over-cap' : ''}>{formatMoney(CAP - totalExposure)} remaining</span>
              </div>
            </div>

            <div className="modal-action">
              <span className="difficulty"><span>Risk tier</span><b>{modalCustomer.riskTier}</b></span>
              <button className="confirm-button" type="button" onClick={continueWithCustomer}>
                Continue with {modalCustomer.name.split(' ')[0]}<ArrowRight size={17} />
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

export default App;
