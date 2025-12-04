import * as courseMock from './mock/course'
import * as courseReal from './real/course'

const useMock = (process.env.VUE_APP_USE_MOCK ?? 'false') == 'true'

export const courseApi = useMock ? courseMock : courseReal