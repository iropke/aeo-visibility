import Link from "next/link";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { isLocale } from "@/lib/i18n/config";
import { LegalArticle, LegalSection } from "@/components/legal/LegalArticle";

export const dynamic = "force-static";

export default async function PrivacyPage({
  params,
}: {
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;
  if (!isLocale(lang)) return null;
  setRequestLocale(lang);

  const t = await getTranslations("app.legal");

  return (
    <LegalArticle
      title={t("privacy.title")}
      subtitle={t("privacy.subtitle")}
      effectiveDate="May 14, 2026"
      effectiveDateLabel={t("effective_date_label")}
    >
      <p>
        This Privacy Policy explains how AHXOV (&ldquo;<strong>AHXOV</strong>&rdquo;,
        &ldquo;<strong>we</strong>&rdquo;, &ldquo;<strong>us</strong>&rdquo;), operated
        by [Company Legal Name], a company organized under the laws of the Republic of
        Korea with its principal place of business at [Business Address], collects, uses,
        discloses, and protects information when you visit ahxov.com or use the AHXOV
        web application, APIs, or related services (the &ldquo;<strong>Service</strong>
        &rdquo;). For the purposes of the EU General Data Protection Regulation (GDPR),
        the UK Data Protection Act 2018, the California Consumer Privacy Act (CCPA), and
        the Personal Information Protection Act of the Republic of Korea (PIPA), AHXOV
        acts as the controller of the personal information described in this policy
        unless otherwise stated.
      </p>

      <LegalSection heading="1. Information We Collect">
        <p>We collect the following categories of information.</p>
        <p>
          <strong>Account Information.</strong> When you create an account, we collect
          your email address, display name, the language and timezone you select, the
          workspace name you create, and any team-member email addresses you invite. We
          authenticate users via magic-link email; we do not store passwords.
        </p>
        <p>
          <strong>Workspace and Analysis Data.</strong> When you add a site or run an
          analysis, we collect the URL, optional nickname, the workspace it belongs to,
          and the analysis configuration (categories selected, trigger type). To
          generate results, we fetch the publicly available content at the URLs you
          provide and store the resulting scores, evidence snippets, AI-generated
          insights, and improvement recommendations.
        </p>
        <p>
          <strong>Billing Information.</strong> When you subscribe to a paid plan, our
          third-party payment processor collects and stores your payment-method details
          (such as the last four digits of your card, card brand, billing country, and
          billing email). AHXOV stores only non-sensitive billing metadata (subscription
          status, plan, renewal date, invoice references); we do not store full payment
          card numbers.
        </p>
        <p>
          <strong>Usage Information.</strong> We collect information about how you use
          the Service, including IP address, browser type, device identifiers, pages
          viewed, features used, request timestamps, and error logs. We use this
          information to operate, secure, and improve the Service.
        </p>
        <p>
          <strong>Cookies and Similar Technologies.</strong> We use strictly necessary
          cookies for authentication and session management. We may use limited
          analytics cookies to understand aggregate usage; where required by law, we
          will request your consent before setting non-essential cookies. You can
          control cookies through your browser settings; disabling necessary cookies may
          break sign-in.
        </p>
        <p>
          <strong>Communications.</strong> If you contact us through the contact form,
          email, or in-app messaging, we collect the content of your communication and
          any information you choose to provide (name, company, email).
        </p>
      </LegalSection>

      <LegalSection heading="2. How We Use Information">
        <p>We use the information we collect to:</p>
        <ul className="list-disc pl-6 space-y-1">
          <li>provide, maintain, and operate the Service, including running analyses;</li>
          <li>
            authenticate users, prevent fraud, and protect the security of the Service;
          </li>
          <li>
            communicate with you about your account, billing, product updates, security
            advisories, and support requests;
          </li>
          <li>
            send transactional email (analysis completion notifications, trial-expiry
            reminders) and, where you have consented or applicable law permits,
            marketing email;
          </li>
          <li>
            generate aggregate, de-identified analytics about Service usage and feature
            adoption;
          </li>
          <li>
            comply with legal obligations, enforce our Terms of Service, and resolve
            disputes.
          </li>
        </ul>
        <p>
          <strong>Legal bases (GDPR / UK).</strong> We rely on the following legal bases:
          (a) performance of a contract to provide the Service you signed up for; (b)
          our legitimate interests in operating, securing, and improving the Service;
          (c) compliance with legal obligations; and (d) your consent, where required.
        </p>
      </LegalSection>

      <LegalSection heading="3. AI Processing">
        <p>
          To generate insights and recommendations, the Service sends analysis inputs
          (such as content extracted from the URLs you submit and structured scoring
          data) to third-party large language model providers, currently Anthropic, Inc.
          (Claude). We have contractual commitments with these providers that they will
          not use your inputs to train their general-purpose models. We do not send
          account credentials, payment information, or other unrelated personal data to
          these providers.
        </p>
      </LegalSection>

      <LegalSection heading="4. How We Share Information">
        <p>We share information only as described below.</p>
        <p>
          <strong>Service Providers.</strong> We share information with vendors that
          process data on our behalf to operate the Service, including hosting
          (Vercel, Supabase), email delivery (Resend), payment processing (our payment
          gateway provider), and AI model inference (Anthropic). These providers are
          bound by contractual confidentiality and data-protection obligations.
        </p>
        <p>
          <strong>Within Your Workspace.</strong> Members of your workspace can view
          shared workspace content (sites, analyses, results) according to their role.
          We do not share Customer Data across workspaces.
        </p>
        <p>
          <strong>Legal and Safety.</strong> We may disclose information when we believe
          in good faith that disclosure is required by law, legal process, or
          governmental request, or is necessary to protect the rights, property, or
          safety of AHXOV, our users, or the public.
        </p>
        <p>
          <strong>Corporate Transactions.</strong> If we are involved in a merger,
          acquisition, financing, reorganization, or sale of assets, information may be
          transferred as part of that transaction, subject to standard confidentiality
          protections.
        </p>
        <p>
          We do not sell personal information, and we do not share personal information
          for cross-context behavioral advertising.
        </p>
      </LegalSection>

      <LegalSection heading="5. International Data Transfers">
        <p>
          AHXOV is based in the Republic of Korea, and we use service providers located
          in various countries, including the United States and the European Union.
          When personal information is transferred outside of your country of residence,
          we rely on appropriate safeguards such as Standard Contractual Clauses or
          equivalent mechanisms recognized under applicable law.
        </p>
      </LegalSection>

      <LegalSection heading="6. Data Retention">
        <p>
          We retain personal information for as long as necessary to provide the Service
          and comply with our legal obligations. Specifically:
        </p>
        <ul className="list-disc pl-6 space-y-1">
          <li>
            <strong>Account information</strong> is retained while your account is
            active and for up to ninety (90) days after account deletion to allow for
            recovery and dispute resolution;
          </li>
          <li>
            <strong>Analysis results</strong> are retained while your workspace is
            active and for the duration documented in your plan tier;
          </li>
          <li>
            <strong>Billing records and tax documents</strong> are retained for the
            periods required by applicable tax and commercial law (typically five (5)
            years in Korea);
          </li>
          <li>
            <strong>Security logs</strong> are retained for up to twelve (12) months for
            fraud prevention and incident response.
          </li>
        </ul>
        <p>
          After the applicable retention period, we delete or anonymize the information,
          unless retention is required by law.
        </p>
      </LegalSection>

      <LegalSection heading="7. Your Rights">
        <p>
          Depending on where you reside, you may have the following rights with respect
          to your personal information: access, correction, deletion, restriction or
          objection to processing, portability, and withdrawal of consent. You can
          exercise many of these rights directly from your account settings, or by
          contacting us at{" "}
          <a className="text-primary hover:underline" href="mailto:privacy@ahxov.com">
            privacy@ahxov.com
          </a>
          . We will respond within the timeframes required by applicable law.
        </p>
        <p>
          <strong>EU / UK residents</strong> have the right to lodge a complaint with
          their local supervisory authority. <strong>California residents</strong> have
          additional rights under the CCPA, including the right to know, delete, correct,
          and opt out of certain sharing. <strong>Korean residents</strong> may exercise
          the rights granted under PIPA and may contact our Privacy Officer at the email
          above.
        </p>
      </LegalSection>

      <LegalSection heading="8. Security">
        <p>
          We implement administrative, technical, and physical safeguards designed to
          protect personal information, including encryption in transit, encryption at
          rest for sensitive data, least-privilege access controls, logging, and regular
          backups. No method of transmission or storage is one hundred percent secure,
          and we cannot guarantee absolute security. If we become aware of a security
          breach affecting your personal information, we will notify you in accordance
          with applicable law.
        </p>
      </LegalSection>

      <LegalSection heading="9. Children's Privacy">
        <p>
          The Service is not directed to children under the age of sixteen (16), and we
          do not knowingly collect personal information from children. If you believe
          that a child has provided personal information to us, please contact{" "}
          <a className="text-primary hover:underline" href="mailto:privacy@ahxov.com">
            privacy@ahxov.com
          </a>{" "}
          and we will take appropriate steps to delete the information.
        </p>
      </LegalSection>

      <LegalSection heading="10. Third-Party Links">
        <p>
          The Service may contain links to third-party websites or services. We are not
          responsible for the privacy practices of those third parties. We encourage you
          to review their privacy policies before providing any personal information.
        </p>
      </LegalSection>

      <LegalSection heading="11. Changes to This Policy">
        <p>
          We may update this Privacy Policy from time to time. If we make material
          changes, we will provide reasonable notice (for example, by posting an updated
          effective date and, where appropriate, by sending email to the workspace
          owner). Your continued use of the Service after the effective date constitutes
          acceptance of the updated policy.
        </p>
      </LegalSection>

      <LegalSection heading="12. Contact">
        <p>
          Questions, complaints, or requests regarding this Privacy Policy or your
          personal information? Contact us at{" "}
          <a className="text-primary hover:underline" href="mailto:privacy@ahxov.com">
            privacy@ahxov.com
          </a>{" "}
          or through the{" "}
          <Link className="text-primary hover:underline" href={`/${lang}/contact`}>
            contact form
          </Link>
          . You can also review our{" "}
          <Link
            className="text-primary hover:underline"
            href={`/${lang}/legal/terms`}
          >
            Terms of Service
          </Link>{" "}
          and{" "}
          <Link
            className="text-primary hover:underline"
            href={`/${lang}/legal/refund`}
          >
            Refund Policy
          </Link>
          .
        </p>
      </LegalSection>
    </LegalArticle>
  );
}
