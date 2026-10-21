export enum memberCategory {
    Alum = 're',
    Faculty_Or_Staff = 'fa',
    Friend_Of_The_Association = 'fr',
}

export function getAllowedTiers(type?: memberCategory): MemberTier[] {
    if (type !== undefined && type !== memberCategory.Alum) {
        return [MemberTier.Contributor, MemberTier.Parton];
    }

    return [MemberTier.Starter, MemberTier.Contributor, MemberTier.Parton];
}

export const memberCategoryDescriptions: Record<memberCategory, string> = {
    re: 'Alum',
    fa: 'Faculty Or Staff',
    fr: 'Friend Of The Association',
};

export enum MemberTier {
    Starter = 'st',
    Contributor = 'co',
    Parton = 'pa',
}

export const MemberTierShortTitles: Record<MemberTier, string> = {
    st: 'Starter',
    co: 'Contributor',
    pa: 'Patron',
}
export const MemberTierTitles: Record<MemberTier, string> = {
    st: '<b>Starter</b> - The free membership for those not ready or willing to financially contribute to the Association at this point. ',
    co: '<b>Contributor</b> - Our standard membership for Alumni and associate members who are part of the community at Constructor University, former Jacobs University.',
    pa: '<b>Patron</b> - Our membership for senior alumni and friends who want to give back even more and celebrate the spirit of Constructor University, former Jacobs University!',
}

export const MemberTierPrices: Record<MemberTier, string> = {
    st: '0€ / year',
    co: '39€ / year',
    pa: '249€ / year'
}

export const MemberTierDescriptions: Record<MemberTier, string> = {
    st: `
        We want all Alumni to be able to connect via the Association and won't exclude anyone based on their financial situation or willingness to contribute.
        For this reason we are offering the free starter tier with the same benefits as the Contributor tier.  
        After the first 2 years (and then once a year after that), we'll check with you if you want to stay in the Starter tier or if you feel comfortable upgrading to one of our paid tiers.
        If you don't, no problem, you can decide to stay in the Starter tier with no disadvantages.
    `,
    co: `
    <ul>
        <li>Your @jacobs-alumni.de email account is hosted on G Suite and comes with access to various apps as well as Google Drive space. </li>
        <li>Voting rights in the General Assembly of the Beyond the Pond Alumni Association. </li>
        <li>Eligibility as a mentee or mentor for 1 year mentoring program. </li>
        <li>Access to Career Counselling Services. </li>
        <li>Free access to career seminars and workshops (on campus). </li>
        <li>Career Fair at Constructor University, former Jacobs University: Free Silver Package (worth 850€) for own start-ups and spin-off companies.</li>
        <li>Career Services for Alumni Employers: 20% discount on Presentations, Recruiting Events, Workshops, Employer Interviews and Pre-Selection.</li>
        <li>Alumni Newsletter to stay up-to-date on all Alumni and University developments</li>
        <li>More to come!</li>
    </ul>
    `,
    pa: `
        <ul>
            <li>All Contributor benefits PLUS</li>
            <li>After three years of patron membership, engraved alumni brick (on the path in front of the IRC)</li>
            <li>Special mention in the Association’s newsletter after joining</li>
            <li>Special mention in yearly newsletter every year of membership</li>
            <li>Enables the Alumni Association to help young and future alumni grow and really make a difference in their lives</li>
        </ul>
    `,
}