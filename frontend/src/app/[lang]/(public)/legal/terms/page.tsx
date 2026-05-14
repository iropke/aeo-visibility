import Link from "next/link";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { isLocale } from "@/lib/i18n/config";
import { LegalArticle, LegalSection } from "@/components/legal/LegalArticle";

export const dynamic = "force-static";

export default async function TermsPage({
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
      title={t("terms.title")}
      subtitle={t("terms.subtitle")}
      effectiveDate="May 14, 2026"
      effectiveDateLabel={t("effective_date_label")}
    >
      <p>
        These Terms of Service (the &ldquo;<strong>Terms</strong>&rdquo;) form a binding
        agreement between you (&ldquo;<strong>you</strong>&rdquo;, &ldquo;<strong>Customer</strong>
        &rdquo;) and AHXOV (&ldquo;<strong>AHXOV</strong>&rdquo;, &ldquo;<strong>we</strong>&rdquo;,
        &ldquo;<strong>us</strong>&rdquo;), operated by [Company Legal Name], a company
        organized under the laws of the Republic of Korea with its principal place of
        business at [Business Address]. By creating an account, accessing, or using
        ahxov.com, the AHXOV web application, related APIs, and any associated services
        (collectively, the &ldquo;<strong>Service</strong>&rdquo;), you agree to be bound
        by these Terms. If you do not agree, do not use the Service.
      </p>

      <LegalSection heading="1. The Service">
        <p>
          AHXOV provides a software-as-a-service platform that measures how visible a
          website is to AI answer engines and large language models, including but not
          limited to technical readiness, structured data, content quality, authority
          signals, and visibility in AI-generated responses. The Service includes
          dashboards, scheduled and on-demand analyses, comparison tools, alerts, email
          reports, and related features that we may add, modify, or remove from time to
          time.
        </p>
      </LegalSection>

      <LegalSection heading="2. Eligibility and Accounts">
        <p>
          You must be at least eighteen (18) years old and have the legal capacity to
          enter into a binding agreement to use the Service. If you use the Service on
          behalf of an organization, you represent that you are authorized to bind that
          organization to these Terms, and &ldquo;you&rdquo; will refer to both you and
          the organization.
        </p>
        <p>
          You are responsible for maintaining the confidentiality of your account
          credentials, for all activities that occur under your account, and for promptly
          notifying us of any unauthorized access at{" "}
          <a className="text-primary hover:underline" href="mailto:security@ahxov.com">
            security@ahxov.com
          </a>
          .
        </p>
      </LegalSection>

      <LegalSection heading="3. Free Trial">
        <p>
          New workspaces receive a free trial of seven (7) days starting on the date the
          workspace is created. No payment method is required to start the trial. During
          the trial, your workspace has access to features and quotas described on the
          Pricing page. At the end of the trial, the workspace becomes read-only until a
          paid subscription is activated. We may modify the length, scope, or
          availability of trials at any time.
        </p>
      </LegalSection>

      <LegalSection heading="4. Subscriptions, Fees, and Billing">
        <p>
          Paid subscriptions renew automatically at the end of each billing cycle
          (monthly or annual, as selected at checkout) until cancelled. Fees are
          presented in U.S. dollars unless otherwise stated and are exclusive of taxes,
          which are added where required by applicable law. Payments are processed by a
          third-party payment processor; by submitting payment information, you
          authorize us and that processor to charge the applicable fees to your selected
          payment method.
        </p>
        <p>
          Quotas (such as the number of sites, competitors, members, and monthly
          analyses) are enforced per workspace and per plan tier. Unused quota does not
          carry over between billing cycles unless explicitly stated for a specific
          add-on. Annual plans are billed up front for the full annual term.
        </p>
        <p>
          Refunds are governed by our{" "}
          <Link
            className="text-primary hover:underline"
            href={`/${lang}/legal/refund`}
          >
            Refund Policy
          </Link>
          , which is incorporated into these Terms by reference.
        </p>
      </LegalSection>

      <LegalSection heading="5. Acceptable Use">
        <p>You agree not to, and not to permit any third party to:</p>
        <ul className="list-disc pl-6 space-y-1">
          <li>
            use the Service to analyze websites that you do not own and for which you do
            not have a legitimate business interest (e.g., competitor research is
            permitted; harassment, doxxing, or de-anonymization is not);
          </li>
          <li>
            submit URLs or content that infringes intellectual property rights, violates
            privacy laws, or contains malware, exploits, or other harmful code;
          </li>
          <li>
            attempt to probe, scan, or test the vulnerability of the Service or any
            associated infrastructure without our prior written consent;
          </li>
          <li>
            reverse engineer, decompile, or attempt to extract the source code of the
            Service except to the extent permitted by applicable law;
          </li>
          <li>
            use the Service to build, train, or improve a competing product or large
            language model, or to scrape Service outputs at scale;
          </li>
          <li>
            resell, sublicense, or otherwise commercially exploit the Service or its
            outputs beyond the rights granted in these Terms;
          </li>
          <li>
            exceed the rate limits, quotas, or other usage limits documented for your
            plan, or evade enforcement of those limits.
          </li>
        </ul>
        <p>
          We may suspend or terminate your access if we reasonably believe you have
          violated this section.
        </p>
      </LegalSection>

      <LegalSection heading="6. Customer Data">
        <p>
          &ldquo;<strong>Customer Data</strong>&rdquo; means information you submit to
          the Service (including URLs, workspace metadata, member information, and
          analysis results derived from your URLs). You retain all right, title, and
          interest in Customer Data. You grant AHXOV a worldwide, non-exclusive,
          royalty-free license to process Customer Data solely to provide, secure, and
          improve the Service in accordance with these Terms and our{" "}
          <Link
            className="text-primary hover:underline"
            href={`/${lang}/legal/privacy`}
          >
            Privacy Policy
          </Link>
          .
        </p>
        <p>
          You represent and warrant that you have all rights necessary to submit
          Customer Data and that your submission and our processing of Customer Data
          will not violate applicable law or any third-party rights.
        </p>
      </LegalSection>

      <LegalSection heading="7. AI Outputs and Third-Party Services">
        <p>
          The Service uses third-party large language models and analytical providers
          (such as Anthropic Claude) to generate insights, scoring, and recommendations
          (&ldquo;<strong>AI Outputs</strong>&rdquo;). AI Outputs are generated
          probabilistically and may contain inaccuracies, omissions, or
          recommendations that are not appropriate for your specific situation. You are
          responsible for reviewing AI Outputs before acting on them. AHXOV does not
          guarantee any particular search visibility, ranking, traffic, or business
          outcome.
        </p>
        <p>
          The Service integrates with third-party services for infrastructure, email
          delivery, payment processing, and analytics. Your use of those services is
          governed by their own terms and policies, and we are not responsible for the
          acts or omissions of third-party providers.
        </p>
      </LegalSection>

      <LegalSection heading="8. Intellectual Property">
        <p>
          The Service, including all software, designs, text, graphics, scoring
          methodologies, documentation, and trademarks, is and remains the exclusive
          property of AHXOV and its licensors. Subject to these Terms, we grant you a
          limited, non-exclusive, non-transferable, revocable license to access and use
          the Service for your internal business purposes during the term of your
          subscription. All rights not expressly granted are reserved.
        </p>
        <p>
          You may submit feedback, suggestions, or ideas about the Service. You grant
          AHXOV a perpetual, irrevocable, worldwide, royalty-free license to use,
          modify, and incorporate that feedback for any purpose without obligation to
          you.
        </p>
      </LegalSection>

      <LegalSection heading="9. Confidentiality">
        <p>
          Each party may receive non-public information of the other party
          (&ldquo;<strong>Confidential Information</strong>&rdquo;). The receiving party
          will use Confidential Information only to perform under these Terms and will
          protect it with at least the same degree of care it uses to protect its own
          confidential information of similar nature, but in no event less than
          reasonable care. Confidential Information does not include information that is
          public through no fault of the receiving party, independently developed
          without use of the disclosing party&rsquo;s information, or required to be
          disclosed by law.
        </p>
      </LegalSection>

      <LegalSection heading="10. Disclaimers">
        <p>
          THE SERVICE IS PROVIDED &ldquo;AS IS&rdquo; AND &ldquo;AS AVAILABLE&rdquo;
          WITHOUT WARRANTIES OF ANY KIND, WHETHER EXPRESS, IMPLIED, OR STATUTORY,
          INCLUDING WITHOUT LIMITATION WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
          PARTICULAR PURPOSE, TITLE, NON-INFRINGEMENT, AND ACCURACY OF AI OUTPUTS. WE DO
          NOT WARRANT THAT THE SERVICE WILL BE UNINTERRUPTED, ERROR-FREE, OR SECURE, OR
          THAT ANY DEFECTS WILL BE CORRECTED.
        </p>
      </LegalSection>

      <LegalSection heading="11. Limitation of Liability">
        <p>
          TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW, IN NO EVENT WILL AHXOV BE
          LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, EXEMPLARY, OR
          PUNITIVE DAMAGES, OR FOR ANY LOSS OF PROFITS, REVENUE, DATA, GOODWILL, OR
          BUSINESS OPPORTUNITY, ARISING OUT OF OR IN CONNECTION WITH THESE TERMS OR THE
          SERVICE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.
        </p>
        <p>
          OUR TOTAL CUMULATIVE LIABILITY ARISING OUT OF OR IN CONNECTION WITH THESE
          TERMS OR THE SERVICE WILL NOT EXCEED THE AMOUNTS YOU PAID TO US FOR THE
          SERVICE IN THE TWELVE (12) MONTHS IMMEDIATELY PRECEDING THE EVENT GIVING RISE
          TO THE CLAIM, OR ONE HUNDRED U.S. DOLLARS (USD 100), WHICHEVER IS GREATER.
        </p>
      </LegalSection>

      <LegalSection heading="12. Indemnification">
        <p>
          You will defend, indemnify, and hold harmless AHXOV and its affiliates,
          officers, employees, and agents from and against any third-party claims,
          damages, liabilities, costs, and expenses (including reasonable
          attorneys&rsquo; fees) arising out of or related to: (a) Customer Data; (b)
          your use of the Service in violation of these Terms or applicable law; or (c)
          your infringement or misappropriation of any third-party right.
        </p>
      </LegalSection>

      <LegalSection heading="13. Termination">
        <p>
          You may cancel your subscription at any time from your workspace settings.
          Upon cancellation, your access continues until the end of the then-current
          billing cycle, after which the workspace becomes read-only. We may suspend or
          terminate your access immediately and without notice if you materially breach
          these Terms, fail to pay fees when due, or use the Service in a manner that
          poses a security or legal risk. Provisions that by their nature should survive
          termination will survive, including Sections 6, 8, 9, 10, 11, 12, 14, and 15.
        </p>
        <p>
          Following termination, we will retain or delete Customer Data in accordance
          with our Privacy Policy and applicable law. You may export your data prior to
          termination using the export features available within the Service.
        </p>
      </LegalSection>

      <LegalSection heading="14. Governing Law and Dispute Resolution">
        <p>
          These Terms are governed by and construed in accordance with the laws of the
          Republic of Korea, without regard to its conflict-of-laws principles. The
          parties agree to submit to the exclusive jurisdiction of the Seoul Central
          District Court for any dispute arising out of or relating to these Terms or
          the Service, except that either party may seek injunctive or equitable relief
          in any court of competent jurisdiction.
        </p>
      </LegalSection>

      <LegalSection heading="15. Changes to These Terms">
        <p>
          We may modify these Terms from time to time. If we make material changes, we
          will provide reasonable notice (for example, by posting an updated effective
          date and, where appropriate, by sending email to the workspace owner). Your
          continued use of the Service after the effective date of the updated Terms
          constitutes acceptance of the changes. If you do not accept the changes, you
          must stop using the Service and may cancel your subscription.
        </p>
      </LegalSection>

      <LegalSection heading="16. Miscellaneous">
        <p>
          These Terms, together with the Privacy Policy and Refund Policy, constitute
          the entire agreement between you and AHXOV regarding the Service and supersede
          all prior or contemporaneous understandings. If any provision of these Terms
          is held to be unenforceable, the remaining provisions will remain in full
          force and effect. Our failure to enforce any provision is not a waiver of that
          provision. You may not assign these Terms without our prior written consent;
          we may assign these Terms in connection with a merger, acquisition, or sale of
          assets. Notices to AHXOV must be sent to{" "}
          <a className="text-primary hover:underline" href="mailto:legal@ahxov.com">
            legal@ahxov.com
          </a>
          .
        </p>
      </LegalSection>

      <LegalSection heading="17. Contact">
        <p>
          Questions about these Terms? Contact us at{" "}
          <a className="text-primary hover:underline" href="mailto:legal@ahxov.com">
            legal@ahxov.com
          </a>{" "}
          or through the{" "}
          <Link className="text-primary hover:underline" href={`/${lang}/contact`}>
            contact form
          </Link>
          .
        </p>
      </LegalSection>
    </LegalArticle>
  );
}
