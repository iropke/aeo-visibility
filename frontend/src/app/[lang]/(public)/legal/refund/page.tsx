import Link from "next/link";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { isLocale } from "@/lib/i18n/config";
import { LegalArticle, LegalSection } from "@/components/legal/LegalArticle";

export const dynamic = "force-static";

export default async function RefundPage({
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
      title={t("refund.title")}
      subtitle={t("refund.subtitle")}
      effectiveDate="May 14, 2026"
      effectiveDateLabel={t("effective_date_label")}
    >
      <p>
        This Refund Policy describes when and how AHXOV (&ldquo;<strong>AHXOV</strong>
        &rdquo;, &ldquo;<strong>we</strong>&rdquo;, &ldquo;<strong>us</strong>&rdquo;)
        issues refunds for paid subscriptions to ahxov.com and related services (the
        &ldquo;<strong>Service</strong>&rdquo;). This Refund Policy is incorporated into,
        and forms part of, our{" "}
        <Link className="text-primary hover:underline" href={`/${lang}/legal/terms`}>
          Terms of Service
        </Link>
        . Capitalized terms not defined here have the meanings given in the Terms.
      </p>

      <LegalSection heading="1. Free Trial">
        <p>
          New workspaces receive a free trial of seven (7) days. No payment method is
          required to start the trial, and no charges are made during the trial. If you
          do not subscribe before the trial ends, your workspace becomes read-only; you
          can subscribe at any time to restore full access. Because no payment is taken
          during the trial, there is nothing to refund.
        </p>
      </LegalSection>

      <LegalSection heading="2. Money-Back Guarantee on First Subscription">
        <p>
          We offer a fourteen (14) day money-back guarantee on your <strong>first</strong>{" "}
          paid subscription for a workspace. If you are not satisfied, contact us at{" "}
          <a className="text-primary hover:underline" href="mailto:billing@ahxov.com">
            billing@ahxov.com
          </a>{" "}
          within fourteen (14) days of your initial paid charge and request a refund.
          We will refund the full amount of the initial charge to your original payment
          method. The money-back guarantee applies only to the first paid subscription
          for a given workspace and does not apply to renewals, upgrades, add-ons, or
          subsequent subscriptions.
        </p>
      </LegalSection>

      <LegalSection heading="3. Monthly Subscriptions">
        <p>
          You may cancel a monthly subscription at any time from your workspace
          settings. Cancellation stops future renewals; the subscription remains active
          until the end of the current billing cycle, after which the workspace becomes
          read-only. Fees already paid for the current billing cycle are{" "}
          <strong>non-refundable</strong> except where required by applicable law or
          where the money-back guarantee in Section 2 applies.
        </p>
      </LegalSection>

      <LegalSection heading="4. Annual Subscriptions">
        <p>
          Annual subscriptions are billed up front for the full annual term and provide
          a discount compared with monthly billing. If you cancel an annual
          subscription, the subscription remains active until the end of the annual
          term, after which the workspace becomes read-only. Annual fees are{" "}
          <strong>non-refundable</strong> after the fourteen (14) day money-back
          guarantee window described in Section 2, except as required by applicable law.
        </p>
        <p>
          On request, we may at our sole discretion offer a pro-rata credit toward a
          future subscription in exceptional cases (e.g., extended Service unavailability
          attributable to AHXOV). Such credits are not transferable and do not constitute
          a guarantee of future refunds.
        </p>
      </LegalSection>

      <LegalSection heading="5. Add-Ons and One-Time Charges">
        <p>
          Pay-as-you-go credits, additional analysis packs, additional seats, and other
          add-ons are <strong>non-refundable</strong> once they have been added to your
          workspace and become available for use, even if you do not consume them within
          a given billing cycle. Unused add-ons may expire as described on the Pricing
          page.
        </p>
      </LegalSection>

      <LegalSection heading="6. Eligibility Exclusions">
        <p>Refunds will not be issued where:</p>
        <ul className="list-disc pl-6 space-y-1">
          <li>
            the request is made after the applicable refund window has closed;
          </li>
          <li>
            we have reasonably determined that the account has violated the Terms,
            including the Acceptable Use provisions;
          </li>
          <li>
            the request relates to a chargeback or dispute that has already been
            resolved with the payment processor (see Section 8);
          </li>
          <li>
            the customer is on an Enterprise plan with custom terms, in which case the
            refund provisions of the applicable order form govern.
          </li>
        </ul>
      </LegalSection>

      <LegalSection heading="7. How to Request a Refund">
        <p>
          Send a refund request from the email address associated with the workspace
          owner to{" "}
          <a className="text-primary hover:underline" href="mailto:billing@ahxov.com">
            billing@ahxov.com
          </a>
          . Include the workspace name, the invoice number, and a brief reason for the
          request. We will respond within five (5) business days. Approved refunds are
          issued to the original payment method within ten (10) business days; the time
          it takes to appear on your statement depends on your card issuer or bank and
          is outside our control.
        </p>
      </LegalSection>

      <LegalSection heading="8. Chargebacks">
        <p>
          If you initiate a chargeback or payment dispute without first contacting us,
          we may suspend or terminate your account pending resolution. We encourage you
          to contact{" "}
          <a className="text-primary hover:underline" href="mailto:billing@ahxov.com">
            billing@ahxov.com
          </a>{" "}
          first so we can resolve billing questions directly and quickly.
        </p>
      </LegalSection>

      <LegalSection heading="9. Currency and Taxes">
        <p>
          Refunds are issued in the original currency of the charge and in the same
          amount as the original charge, net of any payment-processor fees that are not
          recoverable. Where taxes (including VAT or other consumption taxes) were
          collected on the original charge, we will refund the proportional tax amount
          where required by applicable law. Currency conversion differences arising
          between the charge and the refund are the responsibility of the cardholder.
        </p>
      </LegalSection>

      <LegalSection heading="10. Consumer Protection Rights">
        <p>
          Nothing in this Refund Policy limits your statutory rights as a consumer
          under applicable law, including the right of withdrawal under EU consumer
          protection law, rights under the Korean Act on the Consumer Protection in
          Electronic Commerce, or analogous rights in your jurisdiction. Where these
          rights provide a more favorable refund treatment than this Policy, those
          rights prevail.
        </p>
      </LegalSection>

      <LegalSection heading="11. Changes to This Policy">
        <p>
          We may update this Refund Policy from time to time. The effective date at the
          top of this page reflects the current version. Material changes will be
          communicated by reasonable means (such as in-app notice or email to the
          workspace owner). Refunds will be evaluated against the policy in effect on
          the date the original charge was made.
        </p>
      </LegalSection>

      <LegalSection heading="12. Contact">
        <p>
          Billing or refund questions? Contact{" "}
          <a className="text-primary hover:underline" href="mailto:billing@ahxov.com">
            billing@ahxov.com
          </a>{" "}
          or use the{" "}
          <Link className="text-primary hover:underline" href={`/${lang}/contact`}>
            contact form
          </Link>
          . See also our{" "}
          <Link
            className="text-primary hover:underline"
            href={`/${lang}/legal/terms`}
          >
            Terms of Service
          </Link>{" "}
          and{" "}
          <Link
            className="text-primary hover:underline"
            href={`/${lang}/legal/privacy`}
          >
            Privacy Policy
          </Link>
          .
        </p>
      </LegalSection>
    </LegalArticle>
  );
}
