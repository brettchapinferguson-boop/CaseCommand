import { FormEvent, useState } from 'react';

type FormState = {
  name: string;
  company: string;
  email: string;
  phone: string;
  industry: string;
  interest: string;
  message: string;
};

type Errors = Partial<Record<keyof FormState, string>>;

const INDUSTRIES = [
  'Law Firm',
  'Medical Practice',
  'HR / Staffing',
  'Financial Services',
  'Real Estate',
  'Marketing Agency',
  'Professional Services',
  'Consumer-Facing Business',
  'Other',
];

const INTERESTS = [
  'Audit / Governance',
  'Solutions / Bespoke Build',
  'Both — I want to talk through fit',
  'Not sure yet',
];

const initial: FormState = {
  name: '',
  company: '',
  email: '',
  phone: '',
  industry: '',
  interest: '',
  message: '',
};

export default function LeadForm() {
  const [form, setForm] = useState<FormState>(initial);
  const [errors, setErrors] = useState<Errors>({});
  const [submitted, setSubmitted] = useState(false);

  function update<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
    if (errors[key]) {
      setErrors((prev) => ({ ...prev, [key]: undefined }));
    }
  }

  function validate(): Errors {
    const next: Errors = {};
    if (!form.name.trim()) next.name = 'Please enter your name.';
    if (!form.company.trim()) next.company = 'Please enter your company.';
    if (!form.email.trim()) {
      next.email = 'Please enter your email.';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
      next.email = 'Please enter a valid email address.';
    }
    if (form.phone && !/^[+()\-\s\d]{7,}$/.test(form.phone)) {
      next.phone = 'Please enter a valid phone number.';
    }
    if (!form.industry) next.industry = 'Please select an industry.';
    if (!form.interest) next.interest = 'Please pick the closest fit.';
    return next;
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const next = validate();
    setErrors(next);
    if (Object.keys(next).length > 0) return;
    setSubmitted(true);
  }

  function handleReset() {
    setForm(initial);
    setErrors({});
    setSubmitted(false);
  }

  return (
    <section id="consult" className="section-pad bg-white">
      <div className="container-page">
        <div className="grid gap-12 lg:grid-cols-12 lg:gap-16">
          <div className="lg:col-span-5">
            <span className="eyebrow">Get Started</span>
            <h2 className="section-title mt-4">
              Tell Us What You’re Trying To Solve.
            </h2>
            <p className="section-intro">
              Book a 30-minute consultation. We’ll talk through whether your
              first step is an audit, an efficiency review, a build — or some
              combination — and what a working engagement would look like.
            </p>

            <ul role="list" className="mt-8 space-y-4">
              {[
                'A focused 30-minute working conversation',
                'No-pressure scoping for an audit, review, or build',
                'A short summary of the right first step',
              ].map((item) => (
                <li key={item} className="flex items-start gap-3">
                  <span className="mt-1 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-gold-100 text-gold-700">
                    <svg
                      className="h-3 w-3"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="3"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      aria-hidden="true"
                    >
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  </span>
                  <span className="text-base text-charcoal-700">{item}</span>
                </li>
              ))}
            </ul>

            <div className="mt-10 rounded-xl border border-navy-100 bg-navy-50/60 p-5 text-sm text-charcoal-600">
              <p className="font-semibold text-navy-900">A note on legal advice</p>
              <p className="mt-2 leading-relaxed">
                Anchor provides AI governance, compliance, audit, and
                operational consulting. Legal services, if applicable, are
                provided only through a separate attorney-client engagement.
              </p>
            </div>
          </div>

          <div className="lg:col-span-7">
            <div className="rounded-2xl border border-navy-100 bg-white p-7 shadow-card sm:p-9">
              {submitted ? (
                <SuccessState onReset={handleReset} name={form.name} />
              ) : (
                <form noValidate onSubmit={handleSubmit} className="space-y-5">
                  <div className="grid gap-5 sm:grid-cols-2">
                    <Field
                      id="name"
                      label="Name"
                      required
                      value={form.name}
                      error={errors.name}
                      onChange={(v) => update('name', v)}
                      autoComplete="name"
                    />
                    <Field
                      id="company"
                      label="Company"
                      required
                      value={form.company}
                      error={errors.company}
                      onChange={(v) => update('company', v)}
                      autoComplete="organization"
                    />
                  </div>

                  <div className="grid gap-5 sm:grid-cols-2">
                    <Field
                      id="email"
                      label="Email"
                      type="email"
                      required
                      value={form.email}
                      error={errors.email}
                      onChange={(v) => update('email', v)}
                      autoComplete="email"
                    />
                    <Field
                      id="phone"
                      label="Phone"
                      type="tel"
                      value={form.phone}
                      error={errors.phone}
                      onChange={(v) => update('phone', v)}
                      autoComplete="tel"
                    />
                  </div>

                  <div className="grid gap-5 sm:grid-cols-2">
                    <SelectField
                      id="industry"
                      label="Industry"
                      required
                      value={form.industry}
                      placeholder="Select your industry"
                      options={INDUSTRIES}
                      error={errors.industry}
                      onChange={(v) => update('industry', v)}
                    />
                    <SelectField
                      id="interest"
                      label="Primarily interested in"
                      required
                      value={form.interest}
                      placeholder="Choose the closest fit"
                      options={INTERESTS}
                      error={errors.interest}
                      onChange={(v) => update('interest', v)}
                    />
                  </div>

                  <div>
                    <label
                      htmlFor="message"
                      className="block text-sm font-medium text-navy-900"
                    >
                      Message
                    </label>
                    <textarea
                      id="message"
                      name="message"
                      rows={5}
                      value={form.message}
                      onChange={(e) => update('message', e.target.value)}
                      placeholder="Briefly: what prompted you to reach out, and what would a good outcome look like?"
                      className="mt-2 block w-full rounded-md border border-charcoal-200 bg-white px-3.5 py-2.5 text-sm text-charcoal-900 transition-colors hover:border-charcoal-300 focus:border-navy-700 focus:outline-none focus:ring-2 focus:ring-navy-200"
                    />
                  </div>

                  <div className="flex flex-col gap-3 pt-2 sm:flex-row sm:items-center sm:justify-between">
                    <p className="text-xs text-charcoal-500">
                      We respond within one business day. Information is kept
                      confidential.
                    </p>
                    <button
                      type="submit"
                      className="btn-primary w-full sm:w-auto"
                    >
                      Request Consultation
                    </button>
                  </div>
                </form>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

type FieldProps = {
  id: keyof FormState;
  label: string;
  type?: string;
  required?: boolean;
  value: string;
  error?: string;
  onChange: (value: string) => void;
  autoComplete?: string;
};

function Field({
  id,
  label,
  type = 'text',
  required,
  value,
  error,
  onChange,
  autoComplete,
}: FieldProps) {
  const errorId = `${id}-error`;
  return (
    <div>
      <label
        htmlFor={id}
        className="block text-sm font-medium text-navy-900"
      >
        {label} {required && <span className="text-rose-500">*</span>}
      </label>
      <input
        id={id}
        name={id}
        type={type}
        required={required}
        value={value}
        autoComplete={autoComplete}
        onChange={(e) => onChange(e.target.value)}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? errorId : undefined}
        className={`mt-2 block w-full rounded-md border bg-white px-3.5 py-2.5 text-sm text-charcoal-900 transition-colors focus:border-navy-700 focus:outline-none focus:ring-2 focus:ring-navy-200 ${
          error ? 'border-rose-400' : 'border-charcoal-200 hover:border-charcoal-300'
        }`}
      />
      {error && (
        <p id={errorId} className="mt-1.5 text-xs font-medium text-rose-600">
          {error}
        </p>
      )}
    </div>
  );
}

type SelectProps = {
  id: keyof FormState;
  label: string;
  required?: boolean;
  value: string;
  placeholder: string;
  options: string[];
  error?: string;
  onChange: (value: string) => void;
};

function SelectField({
  id,
  label,
  required,
  value,
  placeholder,
  options,
  error,
  onChange,
}: SelectProps) {
  const errorId = `${id}-error`;
  return (
    <div>
      <label
        htmlFor={id}
        className="block text-sm font-medium text-navy-900"
      >
        {label} {required && <span className="text-rose-500">*</span>}
      </label>
      <select
        id={id}
        name={id}
        required={required}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? errorId : undefined}
        className={`mt-2 block w-full appearance-none rounded-md border bg-white px-3.5 py-2.5 text-sm text-charcoal-900 transition-colors focus:border-navy-700 focus:outline-none focus:ring-2 focus:ring-navy-200 ${
          error ? 'border-rose-400' : 'border-charcoal-200 hover:border-charcoal-300'
        }`}
      >
        <option value="" disabled>
          {placeholder}
        </option>
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>
      {error && (
        <p id={errorId} className="mt-1.5 text-xs font-medium text-rose-600">
          {error}
        </p>
      )}
    </div>
  );
}

function SuccessState({ onReset, name }: { onReset: () => void; name: string }) {
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex flex-col items-start gap-4 rounded-lg bg-emerald-50/60 p-6 ring-1 ring-emerald-200"
    >
      <span className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500 text-white">
        <svg
          className="h-6 w-6"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <polyline points="20 6 9 17 4 12" />
        </svg>
      </span>
      <h3 className="font-serif text-2xl font-bold text-navy-900">
        Thank you{name ? `, ${name.split(' ')[0]}` : ''}.
      </h3>
      <p className="text-base text-charcoal-700">
        Your request has been received. A member of the Anchor team will reach
        out within one business day to schedule your consultation.
      </p>
      <button type="button" onClick={onReset} className="btn-outline-navy">
        Submit Another Request
      </button>
    </div>
  );
}
