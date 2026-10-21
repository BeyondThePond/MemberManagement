<script lang="ts">
import { Vue, Component } from 'vue-property-decorator';
import Multiselect from 'vue-multiselect';

import getCookie from "../../base/utils/cookie";
import VueValidatable from "../../base/utils/validate";
import {memberCategory, memberCategoryDescriptions, MemberTier, getAllowedTiers, MemberTierShortTitles, MemberTierDescriptions, MemberTierPrices} from "../../base/utils/membership";

// autocomplete on the most common providers
const emailProviders = [
  "gmail.com",
  "yahoo.com",
  "hotmail.com",
  "gmx.de",
  "web.de",
  "outlook.com",
  "googlemail.com",
  "icloud.com",
  "hotmail.de"
];

// the default birthday
const birthDayDefault = new Date();
birthDayDefault.setFullYear(birthDayDefault.getFullYear() - 24);
const birthDayDefaultString = `${birthDayDefault.getFullYear()}-${(birthDayDefault.getMonth() + 1)
        .toString()
        .padStart(2, "0")}-${birthDayDefault
        .getDate()
        .toString()
        .padStart(2, "0")}`;

@Component({
  components: {
    Multiselect
  }
})
export default class SignupForm extends VueValidatable {
  declare $refs: {
    memberCategory: HTMLInputElement;
    registerForm: HTMLFormElement;
  };

  // form validation
  get formInstance() {
    return this.$refs.registerForm;
  }
  readonly formKeys = ['givenName', 'middleName', 'familyName', 'birthday', 'email', 'memberCategory', 'memberTier', 'nationality', 'tos'];
  readonly validateEndpoint = "/portal/register/validate/";
  readonly submitEndpoint = null;

  // TODO: Split the name handling into a seperate component

  /**
   * given a partial list of names, returns the fullName
   */
  private static joinFullName(givenName: string, middleName: string, familyName: string): string {
    return [givenName, middleName, familyName]
      .filter(a => a !== "")
      .join(" ");
  }

  /** given a full name, split it into indivodual components */
  private static splitFullName(fullName: string): [string, string, string] {
    // split names by spaces into first, middle, last
    const [first, ...middle] = fullName.trim().split(/\s+/g);
    const last = middle.pop();

    // return each component seperatly
    return [
      first,
      middle.join(" "),
      last || ""
    ];
  }

  givenName = this.initialValidationResult.values['givenName'] as string || "";
  middleName = this.initialValidationResult.values['middleName'] as string || "";
  familyName = this.initialValidationResult.values['familyName'] as string || "";
  fullName = SignupForm.joinFullName(this.givenName, this.middleName, this.familyName);
  showDetailedName = this.middleName !== "";

  handleFullNameChange(event: KeyboardEvent & {target: HTMLInputElement}) {
      [this.givenName, this.middleName, this.familyName] = SignupForm.splitFullName(event.target.value || "");
      this.showDetailedName = this.middleName !== "";

      // and also validate
      this.validateFormDebounced()
  }

  handlePartNameChange() {
    this.fullName = SignupForm.joinFullName(this.givenName, this.middleName, this.familyName);
    this.showDetailedName = this.middleName !== "";

    if (!this.showDetailedName) {
      this.$refs.memberCategory.focus();
    }

    // and run validation
    this.validateFormDebounced();
  }

  mapNationalities(values: string[]) {
    return values.map(v => {
      const dict = this.initialValidationResult.choices.nationality as Array<[string, string]>
      const candidate = dict.find(kv => kv[0] == v);
      if(!candidate) return undefined;
      return {"id": candidate[0], "label": candidate[1]};
    }).filter(x => x !== undefined) as  Array<{id: string, label: string}>;
  }

  // nationality
  nationality = this.mapNationalities(this.initialValidationResult.values['nationality'] as string[] || []);
  
  // email
  email = this.initialValidationResult.values["email"] as string|| "";
  showEmailSuggestions = false;

  get emailSuggestions(): string[] {
    const emailParts = this.$data.email.split("@");
    if (!this.email || !emailParts) {
      return [];
    }

    return emailProviders.map(
      providerDomain => emailParts[0] + "@" + providerDomain
    );
  }

  // birthday
  birthday = this.initialValidationResult.values["birthday"] as string|| birthDayDefaultString;

  // memberCategory
  memberCategory: memberCategory = this.initialValidationResult.values["memberCategory"] as memberCategory || memberCategory.Alum;
  showMembershipType = this.memberCategory !== memberCategory.Alum;
  showMembership() {
    this.showMembershipType = true;

      const memberCategory = this.$refs.memberCategory;

      setTimeout(() => memberCategory.focus(), 200);
      setTimeout(
        () => memberCategory.classList.add("uk-form-danger"),
        200
      );
      setTimeout(
        () => memberCategory.classList.remove("uk-form-danger"),
        2000
      );
  }

  // member tier
  memberTier: MemberTier = this.initialValidationResult.values["memberTier"] as MemberTier || "";
    get tierChoices(): Record<string, string> {
    return getAllowedTiers(this.memberCategory).reduce<Record<string, string>>((acc, v) => {
      acc[v] = MemberTierShortTitles[v];
      return acc;
    }, {});
  };

  tierClass(value: string): string {
    return value == this.memberTier ? "uk-card-primary" : "uk-card-default";
  }

  tierId(value: string): string {
    return 'id_tier_' + value;
  }

  tierPrice(value: MemberTier): string {
    return MemberTierPrices[value];
  }

  tierDescription(value: MemberTier): string {
    return MemberTierDescriptions[value];
  }

  tierShortTitle(value: MemberTier): string {
    return MemberTierShortTitles[value];
  }

  // tos, these always need to be re-checked
  tos = false;
  get signUpText(): string {
    return memberCategoryDescriptions[this.memberCategory];
  }

  // csrf token
  csrf_token = getCookie('csrftoken')!;
}
</script>

<template lang="pug">
div
  form.uk-form-horizontal(method='POST' ref='registerForm')
    // csrf
    input(type='hidden' name='csrfmiddlewaretoken' :value='csrf_token')

    // form errors
    .uk-alert-danger.uk-alert(v-for="error in validateResult.errors.__all__")
      p {{ error.message }}

    // name
    .uk-form-row
      #div_id_fullName
        label.uk-form-label(for='id_fullName') Full Name *
        .uk-form-controls
          input#id_fullname.uk-input.uk-margin-bottom(ref='name' maxlength='255' name='fullname' required='' type='text' @input='handleFullNameChange' autocomplete='name' autofocus='' v-model='fullName' placeholder='Jonathan Smith')
          .div(v-show='!showDetailedName')
            .uk-alert-danger.uk-alert(v-for="error in validateResult.errors.givenName")
                p Given Names: {{ error.message }}
            .uk-alert-danger.uk-alert(v-for="error in validateResult.errors.middleName")
                p Middle Names: {{ error.message }}
            .uk-alert-danger.uk-alert(v-for="error in validateResult.errors.familyName")
                p Family Names: {{ error.message }}

      #div_id_givenName.uk-margin-large-left.uk-margin-top(v-show='showDetailedName')
        label.uk-form-label(for='id_givenName') Given Names *
        .uk-form-controls.uk-form-controls-text
          input#id_givenName.uk-input(maxlength='255' name='givenName' v-model='givenName' required='' type='text' @input='handlePartNameChange')
          .uk-alert-danger.uk-alert(v-for="error in validateResult.errors.givenName")
            p {{ error.message }}
      
      #div_id_middleName.uk-margin-large-left(v-show='showDetailedName')
        label.uk-form-label(for='id_middleName') Middle Names
        .uk-form-controls.uk-form-controls-text
          input#id_middleName.uk-input(maxlength='255' name='middleName' type='text' v-model='middleName' @input='handlePartNameChange')
          .uk-alert-danger.uk-alert(v-for="error in validateResult.errors.middleName")
            p {{ error.message }}
      
      #div_id_familyName.uk-margin-large-left(v-show='showDetailedName')
        label.uk-form-label(for='id_familyName') Family Names *
        .uk-form-controls.uk-form-controls-text
          input#id_familyName.uk-input(maxlength='255' name='familyName' v-model='familyName' required='' type='text' @input='handlePartNameChange' ref='familyName')
          .uk-alert-danger.uk-alert(v-for="error in validateResult.errors.familyName")
            p {{ error.message }}
    
    // email
    .uk-form-row
      #div_id_email
        label.uk-form-label(for='id_email') Email *
        .uk-form-controls.uk-form-controls-text
          input#id_email.uk-input(maxlength='254' name='email' required='' type='email' autocomplete='email' list='email-suggestions' placeholder='j.smith@example.com' v-model='email' @change='validateFormDebounced' @focus='showEmailSuggestions = true' @blur='showEmailSuggestions = false')
          datalist#email-suggestions(v-show='showEmailSuggestions')
            option(v-for='suggestion in emailSuggestions' v-bind:key='suggestion' v-bind:value='suggestion')
          .uk-alert-danger.uk-alert(v-for="error in validateResult.errors.email")
            p {{ error.message }}
      
    // birthday
    .uk-form-row
      #div_id_birthday
        label.uk-form-label(for='id_birthday') Birthday *
        .uk-form-controls.uk-form-controls-text
          input#id_birthday.uk-input(name='birthday' required='' type='date' v-model='birthday' @input='validateFormDebounced')
        .uk-alert-danger.uk-alert(v-for="error in validateResult.errors.birthday")
          p {{ error.message }}
    
    // nationality    
    .uk-form-row
          #div_id_nationality
            label.uk-form-label(for='id_nationality') Nationality *
            .uk-form-controls.uk-form-controls-text(id="id_nationality")
              Multiselect(v-model='nationality' :multiple="true" label="label" track-by="id" :options="mapNationalities(initialValidationResult.choices.nationality.map(r => r[0]))")
              .uk-alert-danger.uk-alert(v-for="error in validateResult.errors.nationality")
                p {{ error.message }}
    input(type='hidden' name='nationality' v-for="val in nationality" :value="val.id")

    // membership type
    .uk-form-row(v-show='showMembershipType')
      #div_id_type
        label.uk-form-label(for='id_memberCategory') I am *
        .uk-form-controls.uk-form-controls-text
          select#id_memberCategory.uk-select(name='memberCategory' ref='memberCategory' v-model='memberCategory')
            option(value='re') Alum
            option(value='fa') Faculty Or Staff
            option(value='fr') Friend Of The Association
        
        .uk-alert-danger.uk-alert(v-for="error in validateResult.errors.memberCategory" )
          p {{ error.message }}
    
    // membership tier
    .uk-form-row
      #div_id_tier
        label.uk-form-label(for='id_tier') Your Contribution *
        .uk-form-controls.uk-form-controls-text.uk-grid.uk-grid-small(class="uk-child-width-expand@s")
          .tier-option(v-for='(description, value) in tierChoices' :key='value')
            .uk-card.uk-card-default.uk-card-hover.uk-card-body(:class="tierClass(value)" :id='tierId(value)' @click="memberTier = value")
              h3.uk-card-title {{ tierShortTitle(value) }}
                small  {{ tierPrice(value) }}
              p(v-html="tierDescription(value)")

        .uk-alert-danger.uk-alert(v-for="error in validateResult.errors.memberTier")
          p {{ error.message }}

    input#id_membertier(type='hidden' name='memberTier' :value='memberTier')

    // terms an conditions
    .uk-form-row
      #div_id_tos.uk-margin-bottom.uk-margin-top
        label.uk-form-label(for='id_tos') Terms and Conditions *
        .uk-form-controls.uk-form-controls-text
          input#id_tos.uk-checkbox(name='tos' required='' type='checkbox' v-model='tos')
          |                 I confirm that I have read and agree to the 
          a(href='https://beyondthepondalumni.com/privacy/' target='_blank') Terms and Conditions
          | , the 
          a(href='https://beyondthepondalumni.com/charter' target='_blank') Charter
          | , and the 
          a(href='https://www.jacobs-alumni.de/by-laws' target='_blank') Contributions By-Laws
          | .
          .uk-alert-danger.uk-alert(v-for="error in validateResult.errors.tos")
            p {{ error.message }}

    // submit buttons
    input#input_id_other_type.uk-button.uk-width-1-1.uk-button-default(class='uk-width-1-2@m' value='I Am Not Alum' @click='showMembership' v-show='!showMembershipType')
    input#input_id_submit.uk-button.uk-button-primary(@click.prevent="submitForm" :class="{'uk-width-1-1': showMembershipType, 'uk-width-1-1 uk-width-1-2@m': !showMembershipType}" type='submit' :value="'Sign Up As ' + signUpText")

</template>

<style src="vue-multiselect/dist/vue-multiselect.min.css"></style>

<style>
.tier-option:hover > .uk-card {
  cursor: pointer;
}

.multiselect__tags {
  border-radius: 0;
  font-size: initial;
}

.multiselect__option--highlight {
  background: #084983;
}

.multiselect__tag-icon:focus, .multiselect__tag-icon:hover {
  background: #084983;
}

.multiselect__tag {
  background: #084983;
}

.tier-option ul {
  padding-left: 0;
  list-style-type: "✓  ";
}

.tier-option ul > li {
  margin-bottom: 1em;
}
</style>