try {
    try {
        assert(rs.status().ok)
    } catch (error) {
        if (error.name === 'MongoServerError' && error.codeName === 'NotYetInitialized') {
            console.log('rs.status is not ok, but expected. running rs.initiate()')
            rs.initiate()
            assert(rs.status().ok)
        } else {
            throw error
        }
    }
} catch (error) {
    console.log('error with first startup')
    console.log(error)
    assert(error)
}
console.log('mongo is good')
